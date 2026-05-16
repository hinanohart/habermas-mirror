export interface OpinionOut {
  id: number;
  session_id: string;
  author: string;
  body: string;
  created_at: string;
}

export interface StatementOut {
  id: number;
  session_id: string;
  stage: string;
  body: string;
  provider: string;
  run_id: string;
  created_at: string;
}

export interface SessionOut {
  id: string;
  topic: string;
  created_at: string;
  opinions: OpinionOut[];
  statements: StatementOut[];
}

export interface FacilitateOut {
  session_id: string;
  stages: StatementOut[];
}
