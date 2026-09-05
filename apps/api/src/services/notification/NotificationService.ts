import {
  NotificationChannel,
  NotificationRecord,
} from '@recoverai/shared-types';
import { dataStore } from '../store.js';

export interface SendNotificationInput {
  caseId: string;
  customerId: string;
  channel: NotificationChannel;
  template: string;
  messageBody?: string;
  customerOptedOut?: boolean;
}

export class NotificationService {
  public async sendNotification(
    input: SendNotificationInput,
  ): Promise<NotificationRecord> {
    const notifId = `notif_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;

    // SAFETY CHECK 1: Customer Opt-out Prevention
    if (input.customerOptedOut) {
      const blockedRecord: NotificationRecord = {
        id: notifId,
        caseId: input.caseId,
        customerId: input.customerId,
        channel: input.channel,
        template: input.template,
        status: 'BLOCKED',
        failureReason: 'Customer has explicitly opted out of recovery communications.',
        createdAt: new Date().toISOString(),
      };
      dataStore.saveNotification(blockedRecord);
      return blockedRecord;
    }

    // Mock notification dispatch (zero external PII or real messaging)
    const record: NotificationRecord = {
      id: notifId,
      caseId: input.caseId,
      customerId: input.customerId,
      channel: input.channel,
      template: input.template,
      status: 'SENT',
      messageBody: input.messageBody || `[Mock ${input.channel}] Recovery link for case ${input.caseId}`,
      createdAt: new Date().toISOString(),
      sentAt: new Date().toISOString(),
    };

    dataStore.saveNotification(record);
    return record;
  }
}

export const notificationService = new NotificationService();
