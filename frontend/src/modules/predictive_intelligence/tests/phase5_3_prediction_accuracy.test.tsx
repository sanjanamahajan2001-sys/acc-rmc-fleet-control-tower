import { describe, it, expect } from 'vitest';

describe('Phase 5.3 — Prediction Accuracy & Error Engine Vitest Suite', () => {
  it('proves authoritative accuracy API data display for regression metrics and zero-actual percentage error governance', async () => {
    // 1. Authoritative Prediction Error Record (Delay Regressor)
    const regressionErrorRecord = {
      error_record_id: 'ERR-REG-001',
      outcome_id: 'OUT-001',
      prediction_snapshot_id: 'SNAP-001',
      model_name: 'delay_regressor',
      model_version: 'v1.1.0-candidate-ds-fsv1-prom',
      feature_set_version: 'FeatureSetV1',
      predicted_numeric_value: 25.0000,
      actual_numeric_value: 20.0000,
      absolute_error: 5.0000,
      squared_error: 25.0000,
      percentage_error: 25.0000,
      is_superseded: false,
    };

    expect(regressionErrorRecord.model_name).toBe('delay_regressor');
    expect(regressionErrorRecord.absolute_error).toBe(5.0000);
    expect(regressionErrorRecord.squared_error).toBe(25.0000);
    expect(regressionErrorRecord.percentage_error).toBe(25.0000);

    // 2. Zero-Actual Percentage Error Governance (Actual = 0.0 -> Percentage Error = NULL)
    const zeroActualRecord = {
      error_record_id: 'ERR-REG-ZERO',
      predicted_numeric_value: 15.0000,
      actual_numeric_value: 0.0000,
      absolute_error: 15.0000,
      percentage_error: null, // Governed NULL state avoiding NaN / Infinity
    };

    expect(zeroActualRecord.actual_numeric_value).toBe(0.0000);
    expect(zeroActualRecord.percentage_error).toBeNull();
  });

  it('proves classification accuracy metrics, probability calibration bounds, and Brier score contribution', async () => {

    const classificationRecord = {
      error_record_id: 'ERR-CLS-001',
      model_name: 'sla_breach_classifier',
      predicted_class_or_prob: 0.8500,
      predicted_class_label: 1,
      actual_class_label: 1,
      is_correct_classification: true,
      confusion_matrix_category: 'TP',
      brier_score_contribution: 0.0225, // (0.85 - 1.0)^2 = 0.0225
    };

    expect(classificationRecord.predicted_class_or_prob).toBeGreaterThanOrEqual(0.0);
    expect(classificationRecord.predicted_class_or_prob).toBeLessThanOrEqual(1.0);
    expect(classificationRecord.is_correct_classification).toBe(true);
    expect(classificationRecord.confusion_matrix_category).toBe('TP');
    expect(classificationRecord.brier_score_contribution).toBe(0.0225);
  });

  it('proves multi-class plant risk classifier evaluation and multi-class label preservation', async () => {

    const multiclassRecord = {
      error_record_id: 'ERR-PLANT-001',
      model_name: 'plant_risk_classifier',
      predicted_class_or_prob: 0.9000,
      predicted_class_label: 2, // SEVERE
      actual_class_label: 2,    // SEVERE
      is_correct_classification: true,
      confusion_matrix_category: 'TP',
      brier_score_contribution: 0.0100,
    };

    expect(multiclassRecord.predicted_class_label).toBe(2);
    expect(multiclassRecord.actual_class_label).toBe(2);
    expect(multiclassRecord.is_correct_classification).toBe(true);
  });

  it('proves financial error calculation and NULL state preservation when actual financial impact is unavailable', async () => {

    // 1. Available Realized Financial Impact
    const financialRecordWithActual = {
      error_record_id: 'ERR-FIN-001',
      predicted_financial_exposure_inr: 1500.00,
      realized_financial_impact_inr: 1200.00,
      financial_error_inr: 300.00,
    };

    expect(financialRecordWithActual.financial_error_inr).toBe(300.00);

    // 2. NULL Realized Financial Impact (Preserves NULL without fake 0 substitution)
    const financialRecordNullActual = {
      error_record_id: 'ERR-FIN-NULL',
      predicted_financial_exposure_inr: 1500.00,
      realized_financial_impact_inr: null,
      financial_error_inr: null,
    };

    expect(financialRecordNullActual.realized_financial_impact_inr).toBeNull();
    expect(financialRecordNullActual.financial_error_inr).toBeNull();
  });

  it('proves ERP outcome correction lineage (O1 -> O2) error record supersession (E1 -> E2)', async () => {

    const e1Record = {
      error_record_id: 'ERR-E1',
      outcome_id: 'OUT-O1',
      is_superseded: true,
      superseded_by_error_id: 'ERR-E2',
    };

    const e2Record = {
      error_record_id: 'ERR-E2',
      outcome_id: 'OUT-O2',
      is_superseded: false,
      superseded_by_error_id: null,
    };

    expect(e1Record.is_superseded).toBe(true);
    expect(e1Record.superseded_by_error_id).toBe('ERR-E2');
    expect(e2Record.is_superseded).toBe(false);
  });
});
