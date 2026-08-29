/**
 * Add clinical entry form (FR-D2).
 *
 * Rendered inside the doctor's patient record screen. Only the doctor with a
 * treatment relationship can submit; the backend repeats that check.
 */
import { useState } from 'react';

import { Alert } from '../../components/Feedback';
import FormField from '../../components/FormField';
import { createRecord } from './recordApi';
import { RECORD_TYPES } from './recordTypes';

/** Today as an ISO 8601 date, used as the default and maximum visit date. */
function todayIso() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(
    now.getDate()
  ).padStart(2, '0')}`;
}

export default function AddRecordForm({ patientId, onCreated }) {
  const [form, setForm] = useState({
    visit_date: todayIso(),
    record_type: 'consultation',
    title: '',
    symptoms: '',
    examination: '',
    diagnosis: '',
    treatment: '',
    follow_up: '',
  });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
    setErrors({ ...errors, [event.target.name]: '' });
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const found = {};
    if (form.title.trim().length < 3) found.title = 'Enter a short title for this entry.';
    if (form.diagnosis.trim().length < 3) found.diagnosis = 'A diagnosis is required.';
    if (!form.visit_date) found.visit_date = 'Select the visit date.';
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      await createRecord({
        patient_id: patientId,
        visit_date: form.visit_date,
        record_type: form.record_type,
        title: form.title.trim(),
        symptoms: form.symptoms.trim() || null,
        examination: form.examination.trim() || null,
        diagnosis: form.diagnosis.trim(),
        treatment: form.treatment.trim() || null,
        follow_up: form.follow_up.trim() || null,
      });
      onCreated();
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      style={{
        border: '1px solid var(--ju-border)',
        borderRadius: 'var(--ju-radius)',
        padding: 'var(--ju-space-4)',
        marginBottom: 'var(--ju-space-4)',
        background: 'var(--ju-bg)',
      }}
    >
      <h3 className="ju-card__title">New Clinical Entry</h3>
      <Alert tone="error">{error}</Alert>

      <div className="ju-form-grid">
        <FormField
          label="Visit Date"
          name="visit_date"
          type="date"
          value={form.visit_date}
          onChange={handleChange}
          required
          max={todayIso()}
          error={errors.visit_date}
        />
        <FormField
          label="Record Type"
          name="record_type"
          value={form.record_type}
          onChange={handleChange}
          required
          options={RECORD_TYPES}
        />
        <FormField
          label="Entry Title"
          name="title"
          value={form.title}
          onChange={handleChange}
          required
          error={errors.title}
          placeholder="Acute viral fever"
        />
      </div>

      <div style={{ display: 'grid', gap: 'var(--ju-space-4)', marginTop: 'var(--ju-space-4)' }}>
        <FormField
          label="Reported Symptoms"
          name="symptoms"
          value={form.symptoms}
          onChange={handleChange}
          rows={3}
        />
        <FormField
          label="Examination Findings"
          name="examination"
          value={form.examination}
          onChange={handleChange}
          rows={3}
        />
        <FormField
          label="Diagnosis"
          name="diagnosis"
          value={form.diagnosis}
          onChange={handleChange}
          required
          rows={3}
          error={errors.diagnosis}
        />
        <FormField
          label="Treatment and Advice"
          name="treatment"
          value={form.treatment}
          onChange={handleChange}
          rows={3}
        />
        <FormField
          label="Follow-up Plan"
          name="follow_up"
          value={form.follow_up}
          onChange={handleChange}
          rows={2}
        />
      </div>

      <div className="ju-form-actions">
        <button type="submit" className="ju-btn ju-btn--primary" disabled={submitting}>
          {submitting ? 'Saving Entry…' : 'Save Clinical Entry'}
        </button>
      </div>
    </form>
  );
}
