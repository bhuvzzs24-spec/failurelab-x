/** Phase 3 integration contracts only. No analysis/repair engine is implemented. */
export type EvidenceReference = {
  artifactId: string;
  relation: "supports" | "contradicts" | "unknown";
};
export type Hypothesis = {
  id: string;
  statement: string;
  evidence: EvidenceReference[];
  confidence: number | null;
  uncertainty: string;
  proposedInterventions: string[];
};
export type SequenceEvent = {
  id: string;
  timestamp: number;
  operation: string;
  artifactIds: string[];
};
export type MinimizationResult = {
  original: SequenceEvent[];
  reduced: SequenceEvent[];
  removedIds: string[];
  attempts: number;
  reproduced: number;
  evidenceIds: string[];
};
export type VerificationComparison = {
  sourceVersion: string;
  candidateVersion: string;
  conditions: {
    name: string;
    original: "PASS" | "FAIL" | "INCONCLUSIVE";
    candidate: "PASS" | "FAIL" | "INCONCLUSIVE";
    evidenceIds: string[];
  }[];
};
