import {
  Transaction,
  RiskAssessment,
  RecoveryAction,
  Decision,
} from '@recoverai/shared-types';
import { ScoredAction } from '@recoverai/decision-engine';

export interface DecisionExplanationInput {
  transaction: Transaction;
  riskAssessment: RiskAssessment;
  decision: Decision;
  candidateScores: ScoredAction[];
  selectedAction: RecoveryAction;
}

export interface DecisionExplanationOutput {
  summary: string;
  failureDiagnosis: string;
  riskExplanation: string;
  actionRationale: string;
  rejectedActionsExplanation: string;
  customerCommunicationDraft?: string | undefined;
}

export class GeminiAgentService {
  private apiKey?: string | undefined;

  constructor() {
    if (process.env.GEMINI_API_KEY) {
      this.apiKey = process.env.GEMINI_API_KEY;
    }
  }

  public async explainDecision(
    input: DecisionExplanationInput,
  ): Promise<DecisionExplanationOutput> {
    const { transaction, riskAssessment, decision, candidateScores, selectedAction } = input;

    const rejected = candidateScores.filter((s) => s.action !== selectedAction);
    const rejectedText = rejected
      .map((r) => `${r.action} (EU: ₹${r.expectedUtility.toFixed(2)}, P: ${(r.recoveryProbability * 100).toFixed(0)}%)`)
      .join(', ');

    const defaultOutput: DecisionExplanationOutput = {
      summary: `Transaction ${transaction.id} for ₹${(transaction.amount / 100).toFixed(2)} failed due to ${transaction.failureCategory || 'payment failure'}.`,
      failureDiagnosis: `Failure classified as ${transaction.failureCategory || 'UNKNOWN'}${transaction.failureCode ? ` (${transaction.failureCode})` : ''}.`,
      riskExplanation: `Assessed risk level is ${riskAssessment.riskLevel} (score: ${riskAssessment.riskScore.toFixed(2)}).`,
      actionRationale: `${selectedAction} selected via Expected Utility optimization (EU: ₹${(decision.expectedUtility || 0).toFixed(2)}). ${decision.rationale}`,
      rejectedActionsExplanation: `Rejected alternative actions: ${rejectedText || 'None'}.`,
      customerCommunicationDraft:
        selectedAction === RecoveryAction.PAYMENT_LINK
          ? `Hi! Your recent payment of ₹${(transaction.amount / 100).toFixed(2)} couldn't be completed. Tap to complete: {{payment_link}}`
          : undefined,
    };

    if (!this.apiKey) {
      return defaultOutput;
    }

    try {
      const prompt = `You are RecoverAI's Explanation Assistant. Explain this payment recovery decision strictly based on structured ML inputs.
Transaction Amount: ₹${(transaction.amount / 100).toFixed(2)}
Failure Category: ${transaction.failureCategory || 'UNKNOWN'}
Risk Level: ${riskAssessment.riskLevel} (score: ${riskAssessment.riskScore})
Selected Action: ${selectedAction}
Expected Utility: ₹${decision.expectedUtility || 0}
Rationale: ${decision.rationale}

Output a concise JSON with keys: summary, failureDiagnosis, riskExplanation, actionRationale, rejectedActionsExplanation.`;

      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${this.apiKey}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }],
            generationConfig: { responseMimeType: 'application/json' },
          }),
        },
      );

      if (!response.ok) {
        return defaultOutput;
      }

      const data: any = await response.json();
      const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
      if (text) {
        const parsed = JSON.parse(text);
        return {
          ...defaultOutput,
          summary: parsed.summary || defaultOutput.summary,
          failureDiagnosis: parsed.failureDiagnosis || defaultOutput.failureDiagnosis,
          riskExplanation: parsed.riskExplanation || defaultOutput.riskExplanation,
          actionRationale: parsed.actionRationale || defaultOutput.actionRationale,
          rejectedActionsExplanation: parsed.rejectedActionsExplanation || defaultOutput.rejectedActionsExplanation,
        };
      }
    } catch {
      // Fallback
    }

    return defaultOutput;
  }
}

export const geminiAgentService = new GeminiAgentService();
