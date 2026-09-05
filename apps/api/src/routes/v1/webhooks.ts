import { Router } from 'express';
import type { Request, Response, NextFunction } from 'express';
import {
  Transaction,
  TransactionStatus,
  RecoveryCaseState,
  RecoveryAction,
  RecoveryStatus,
  AuditEventType,
} from '@recoverai/shared-types';
import { config } from '../../config/env.js';
import { dataStore } from '../../services/store.js';
import { recoveryOrchestrator } from '../../services/orchestrator/RecoveryOrchestrator.js';
import { RazorpayWebhookVerifier } from '../../services/payment/RazorpayWebhookVerifier.js';
import { RazorpayFailureMapper } from '../../services/payment/RazorpayFailureMapper.js';

const webhooksRouter = Router();

/**
 * POST /api/v1/webhooks/razorpay
 *
 * Ingestion endpoint for Razorpay Sandbox webhooks.
 * Enforces HMAC-SHA256 signature verification, event deduplication,
 * taxonomy mapping, and autonomous safety-bounded recovery.
 */
webhooksRouter.post('/razorpay', async (req: Request, res: Response, next: NextFunction) => {
  try {
    // 1. Capture exact raw request body
    const rawBody = (req as any).rawBody
      ? (req as any).rawBody
      : Buffer.from(JSON.stringify(req.body || {}), 'utf8');

    // 2. Verify X-Razorpay-Signature header
    const signature = req.headers['x-razorpay-signature'] as string | undefined;
    const webhookSecret = config.razorpayWebhookSecret || process.env['RAZORPAY_WEBHOOK_SECRET'];

    const isValidSignature = RazorpayWebhookVerifier.verifySignature(rawBody, signature, webhookSecret);
    if (!isValidSignature) {
      res.status(400).json({
        success: false,
        error: { message: 'Invalid or missing webhook signature' },
      });
      return;
    }

    // 3. Validate Event Structure
    const event = req.body?.event;
    const eventId = req.body?.event_id || req.body?.id || (req.body?.payload?.payment?.entity?.id ? `${event}_${req.body?.payload?.payment?.entity?.id}` : undefined);

    if (!event || !eventId) {
      res.status(400).json({
        success: false,
        error: { message: 'Invalid webhook payload: missing event or event ID' },
      });
      return;
    }

    // 4. Duplicate Event Protection (Idempotency)
    const idempotencyKey = `idem_wh_${eventId}`;
    const isFresh = await dataStore.checkAndSetIdempotency(idempotencyKey);
    if (!isFresh) {
      res.status(200).json({
        success: true,
        status: 'duplicate_ignored',
      });
      return;
    }

    // 5. Handle Webhook Events
    if (event === 'payment.failed') {
      const paymentEntity = req.body?.payload?.payment?.entity;
      if (!paymentEntity || !paymentEntity.id || !paymentEntity.amount || paymentEntity.amount <= 0) {
        res.status(400).json({
          success: false,
          error: { message: 'Invalid payment.failed payload: missing payment entity or amount' },
        });
        return;
      }

      // Map failure into RecoverAI taxonomy
      const mapped = RazorpayFailureMapper.mapFailure(paymentEntity);

      const txnId = paymentEntity.id;
      const merchantId = paymentEntity.notes?.merchantId || 'merch_rzp_sandbox';
      const customerId = paymentEntity.notes?.customerId || paymentEntity.customer_id || `cust_${paymentEntity.contact?.slice(-4) || 'unknown'}`;

      const txn: Transaction = {
        id: txnId,
        merchantId,
        customerId,
        amount: paymentEntity.amount,
        currency: paymentEntity.currency || 'INR',
        status: TransactionStatus.FAILED,
        failureCategory: mapped.category,
        failureCode: mapped.code,
        deviceChanged: Boolean(paymentEntity.notes?.deviceChanged),
        locationChanged: Boolean(paymentEntity.notes?.locationChanged),
        createdAt: new Date(paymentEntity.created_at ? paymentEntity.created_at * 1000 : Date.now()).toISOString(),
        updatedAt: new Date().toISOString(),
        metadata: {
          paymentMethod: paymentEntity.method,
          errorSource: paymentEntity.error_source,
          errorReason: paymentEntity.error_reason,
          errorDescription: paymentEntity.error_description,
        },
      };

      // Ingest into RecoveryOrchestrator pipeline
      const newCase = await recoveryOrchestrator.createCase(txn);

      // Support opt-out flag from metadata/notes
      if (paymentEntity.notes?.customerOptedOut === 'true' || paymentEntity.notes?.customerOptedOut === true) {
        newCase.customerOptedOut = true;
        await dataStore.saveCase(newCase);
      }

      // Analyze case through ML, Decision, Policy & Gemini explanation
      await recoveryOrchestrator.analyzeCase(newCase.id);

      // Execute action strictly through server-side safety gate
      const executedCase = await recoveryOrchestrator.executeAction(newCase.id, `idem_exec_${newCase.id}_0`);

      res.status(200).json({
        success: true,
        event: 'payment.failed',
        caseId: newCase.id,
        state: executedCase.state,
        action: executedCase.selectedAction,
      });
      return;
    }

    if (event === 'payment_link.paid') {
      const linkEntity = req.body?.payload?.payment_link?.entity;
      const paymentEntity = req.body?.payload?.payment?.entity;

      if (!linkEntity || !linkEntity.id) {
        res.status(400).json({
          success: false,
          error: { message: 'Invalid payment_link.paid payload: missing entity' },
        });
        return;
      }

      const allCases = await dataStore.getAllCases();
      const targetCase = allCases.find(
        (c) =>
          c.transactionId === linkEntity.reference_id ||
          c.id === linkEntity.notes?.caseId ||
          c.transactionId === linkEntity.notes?.transactionId ||
          c.selectedAction === RecoveryAction.PAYMENT_LINK,
      );

      if (targetCase) {
        // Prevent double counting if already recovered
        if (targetCase.state === RecoveryCaseState.RECOVERED) {
          res.status(200).json({
            success: true,
            status: 'already_recovered',
            caseId: targetCase.id,
          });
          return;
        }

        targetCase.state = RecoveryCaseState.RECOVERED;
        targetCase.resolvedAt = new Date().toISOString();
        targetCase.updatedAt = new Date().toISOString();
        await dataStore.saveCase(targetCase);

        // Update transaction to CAPTURED
        const txn = await dataStore.getTransaction(targetCase.transactionId);
        if (txn) {
          txn.status = TransactionStatus.CAPTURED;
          txn.updatedAt = new Date().toISOString();
          await dataStore.saveTransaction(txn);
        }

        const amountRecovered = linkEntity.amount_paid || linkEntity.amount || targetCase.amount;

        // Record immutable audit log
        await dataStore.addAuditEvent({
          id: `evt_wh_rec_${targetCase.id}_${Date.now()}`,
          caseId: targetCase.id,
          transactionId: targetCase.transactionId,
          eventType: AuditEventType.PAYMENT_RECOVERED,
          actor: 'SYSTEM',
          timestamp: new Date().toISOString(),
          reason: `Payment successfully recovered via Razorpay payment_link.paid webhook (${linkEntity.id}).`,
          details: {
            paymentLinkId: linkEntity.id,
            paymentId: paymentEntity?.id,
            amountRecovered,
          },
        });

        // Update attempt record
        const attempts = await dataStore.getAttemptsByCaseId(targetCase.id);
        const linkAttempt = attempts.find((a) => a.action === RecoveryAction.PAYMENT_LINK);
        if (linkAttempt) {
          linkAttempt.status = RecoveryStatus.SUCCEEDED;
          linkAttempt.resolvedAt = new Date().toISOString();
          linkAttempt.amountRecovered = amountRecovered;
          await dataStore.saveAttempt(linkAttempt);
        }

        res.status(200).json({
          success: true,
          event: 'payment_link.paid',
          caseId: targetCase.id,
          state: targetCase.state,
          amountRecovered,
        });
        return;
      }

      res.status(200).json({
        success: true,
        event: 'payment_link.paid',
        status: 'case_not_found',
      });
      return;
    }

    if (event === 'payment_link.expired' || event === 'payment_link.cancelled') {
      const linkEntity = req.body?.payload?.payment_link?.entity;
      if (!linkEntity || !linkEntity.id) {
        res.status(400).json({
          success: false,
          error: { message: `Invalid ${event} payload: missing entity` },
        });
        return;
      }

      const allCases = await dataStore.getAllCases();
      const targetCase = allCases.find(
        (c) =>
          c.transactionId === linkEntity.reference_id ||
          c.id === linkEntity.notes?.caseId ||
          c.transactionId === linkEntity.notes?.transactionId ||
          c.selectedAction === RecoveryAction.PAYMENT_LINK,
      );

      if (targetCase) {
        // Record audit event — do NOT falsely mark as recovered
        await dataStore.addAuditEvent({
          id: `evt_wh_link_${Date.now()}`,
          caseId: targetCase.id,
          transactionId: targetCase.transactionId,
          eventType: AuditEventType.RECOVERY_STOPPED,
          actor: 'SYSTEM',
          timestamp: new Date().toISOString(),
          reason: `Payment link status updated by webhook: ${event} (${linkEntity.id}).`,
          details: { paymentLinkId: linkEntity.id, event },
        });

        // Update attempt status
        const attempts = await dataStore.getAttemptsByCaseId(targetCase.id);
        const linkAttempt = attempts.find((a) => a.action === RecoveryAction.PAYMENT_LINK);
        if (linkAttempt) {
          linkAttempt.status = event === 'payment_link.expired' ? RecoveryStatus.FAILED : RecoveryStatus.CANCELLED;
          linkAttempt.resolvedAt = new Date().toISOString();
          await dataStore.saveAttempt(linkAttempt);
        }

        // If attempts reached limit, transition case to STOPPED
        if (targetCase.attemptCount >= 2 && targetCase.state !== RecoveryCaseState.RECOVERED) {
          targetCase.state = RecoveryCaseState.STOPPED;
          targetCase.updatedAt = new Date().toISOString();
          await dataStore.saveCase(targetCase);
        }

        res.status(200).json({
          success: true,
          event,
          caseId: targetCase.id,
          state: targetCase.state,
        });
        return;
      }

      res.status(200).json({
        success: true,
        event,
        status: 'case_not_found',
      });
      return;
    }

    // Default response for other valid Razorpay webhook events
    res.status(200).json({
      success: true,
      status: 'event_ignored',
      event,
    });
  } catch (err) {
    next(err);
  }
});

export default webhooksRouter;
