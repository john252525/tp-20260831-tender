export const TENDER_STATUSES = [
  'NEW', 'DOCUMENTS_LOADING', 'DOCUMENTS_LOADED', 'PROCESSING',
  'SEMANTIC_FILTERING', 'RELEVANT', 'UNCERTAIN', 'NOT_RELEVANT',
  'SCORING', 'SCORED', 'AWAITING_SUPPLIER_SEARCH',
  'SUPPLIER_SEARCH_IN_PROGRESS', 'SUPPLIERS_FOUND', 'NO_SUPPLIERS_FOUND',
  'AWAITING_CP', 'CP_REQUESTED', 'CP_PARTIALLY_RECEIVED',
  'CP_FULLY_RECEIVED', 'NEGOTIATING', 'READY_FOR_DECISION',
  'APPROVED', 'REJECTED', 'ERROR',
] as const;

export const SUPPLIER_TYPES = ['manufacturer', 'distributor', 'wholesaler', 'retail', 'unknown'] as const;

export const RISK_LEVELS = ['LOW', 'MEDIUM', 'HIGH'] as const;

export const TASK_TYPES = ['SYNC_TENDERS', 'PROCESS_TENDER', 'SEARCH_SUPPLIERS', 'SEND_COMMUNICATIONS', 'PARSE_CP', 'NEGOTIATE'] as const;

export const TASK_STATUSES = ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED'] as const;

export const MESSAGE_TYPES = ['cp_request', 'cp_response', 'clarification', 'negotiation', 'reminder', 'auto_reply', 'manual', 'other'] as const;

export const COMMUNICATION_CHANNELS = ['email', 'telegram', 'whatsapp', 'web_form'] as const;

export const WEBHOOK_EVENTS = ['tender.ready_for_decision', 'cp.received', 'task.completed', 'task.failed'] as const;

export const SETTINGS_SECTIONS = ['company', 'scoring', 'communication', 'tender_source', 'ml', 'templates', 'filters'] as const;

export const MATCH_TYPES = ['exact', 'analog', 'not_found'] as const;

export const DECISION_TYPES = ['APPROVED', 'REJECTED', 'NEEDS_MORE_INFO'] as const;

export const REJECT_REASONS = ['low_margin', 'high_risk', 'not_interested', 'other'] as const;

export const RETURN_TO_STAGES = ['negotiation', 'cp_request'] as const;

export const NEGOTIATION_ACTIONS = ['request_clarification', 'request_discount', 'request_both'] as const;

export const REPROCESS_STAGES = ['DOCUMENTS_LOADING', 'SEMANTIC_FILTERING', 'SCORING', 'SUPPLIER_SEARCH'] as const;