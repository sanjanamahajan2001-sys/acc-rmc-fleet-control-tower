import { env } from '../../../config/env';
export interface OperationalIntelligenceSectionConfig {
  id: string;
  title: string;
  description: string;
  enabled: boolean;
  order: number;
  backendEndpoint: string;
}

export const SECTION_REGISTRY_CONFIGS: Record<string, OperationalIntelligenceSectionConfig> = {
  SECTION_01_OPERATIONAL_HEALTH: {
    id: 'SECTION_01_OPERATIONAL_HEALTH',
    title: 'Operational Health & Executive Index',
    description: 'Authoritative operational health scores derived from PostgreSQL dispatches, SWI, and alert state',
    enabled: true,
    order: 1,
    backendEndpoint: env.VITE_API_BASE_URL + '/operational-intelligence/health',
  },
  SECTION_02_ALERTS_INTELLIGENCE: {
    id: 'SECTION_02_ALERTS_INTELLIGENCE',
    title: 'Operational Alert Intelligence',
    description: 'Active critical exceptions, SLA risk warnings, and unresolved bottlenecks from WS-07 Alert Center',
    enabled: true,
    order: 2,
    backendEndpoint: env.VITE_API_BASE_URL + '/operational-intelligence/alerts',
  },
  SECTION_03_DECISION_RECOMMENDATIONS: {
    id: 'SECTION_03_DECISION_RECOMMENDATIONS',
    title: 'Actionable Decision Recommendations',
    description: 'Rule-assisted dispatch recommendations derived from RecommendationEngine authority',
    enabled: true,
    order: 3,
    backendEndpoint: env.VITE_API_BASE_URL + '/operational-intelligence/recommendations',
  },
  SECTION_04_FINANCIAL_EXPOSURE: {
    id: 'SECTION_04_FINANCIAL_EXPOSURE',
    title: 'Financial Loss & SLA Risk Exposure',
    description: 'Quantified cost exposure derived from dispatches and configured rate tables',
    enabled: true,
    order: 4,
    backendEndpoint: env.VITE_API_BASE_URL + '/operational-intelligence/financial',
  },
  SECTION_05_FLEET_EFFICIENCY: {
    id: 'SECTION_05_FLEET_EFFICIENCY',
    title: 'Fleet & Plant Operational Efficiency',
    description: 'Asset utilization, trips per vehicle, loading turnaround, and cycle times',
    enabled: true,
    order: 5,
    backendEndpoint: env.VITE_API_BASE_URL + '/operational-intelligence/efficiency',
  },
  SECTION_06_COST_EXPOSURE: {
    id: 'SECTION_06_COST_EXPOSURE',
    title: 'Cost & Exposure Intelligence',
    description: 'Realized operational financial exposure, SLA penalties, high-cost operations, and model prediction provenance',
    enabled: true,
    order: 6,
    backendEndpoint: env.VITE_API_BASE_URL + '/operational-intelligence/cost-exposure',
  },
  SECTION_07_INCIDENT_TIMELINE: {
    id: 'SECTION_07_INCIDENT_TIMELINE',
    title: 'High-Resolution Incident Timeline',
    description: 'Chronological reconstruction of dispatch lifecycle events and delays',
    enabled: false, // Pending Phase 7
    order: 7,
    backendEndpoint: env.VITE_API_BASE_URL + '/site-dashboard/gantt',
  },
};
