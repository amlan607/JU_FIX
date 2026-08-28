/**
 * Doctor prescription editor (FR-D1).
 *
 * Route: `/doctor/prescriptions`. A draft can be edited freely; issuing freezes
 * the medicine list and publishes it to the patient and the pharmacy.
 */
import { useCallback, useEffect, useState } from 'react';

import { Alert, EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import StatusChip from '../../components/StatusChip';
import { fetchAuthorisedPatients } from '../records/recordApi';
import MedicineTable from './MedicineTable';
import {
  cancelPrescription,
  createPrescription,
  fetchWrittenPrescriptions,
  issuePrescription,
} from './prescriptionApi';

/** An empty medicine line used when the doctor adds a row. */
const EMPTY_ITEM = { medicine_name: '', dosage: '', frequency: '', duration: '', instructions: '' };

export default function PrescriptionEditorPage() {
  const [prescriptions, setPrescriptions] = useState([]);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [banner, setBanner] = useState('');
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [openId, setOpenId] = useState(null);

  const [form, setForm] = useState({ patient_id: '', diagnosis: '', advice: '' });
  const [items, setItems] = useState([{ ...EMPTY_ITEM }]);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const [written, authorised] = await Promise.all([
        fetchWrittenPrescriptions(),
        fetchAuthorisedPatients(),
      ]);
      setPrescriptions(written);
      setPatients(authorised);
    } catch (apiError) {
      setLoadError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleFormChange = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
    setFormError('');
  };

  const handleItemChange = (index, field, value) => {
    setItems((previous) =>
      previous.map((item, position) => (position === index ? { ...item, [field]: value } : item))
    );
    setFormError('');
  };

  const addItem = () => setItems((previous) => [...previous, { ...EMPTY_ITEM }]);

  const removeItem = (index) =>
    setItems((previous) => (previous.length === 1 ? previous : previous.filter((_, p) => p !== index)));

  const resetForm = () => {
    setForm({ patient_id: '', diagnosis: '', advice: '' });
    setItems([{ ...EMPTY_ITEM }]);
  };

  const handleCreate = async (event) => {
    event.preventDefault();

    if (!form.patient_id) {
      setFormError('Select the patient this prescription is for.');
      return;
    }
    if (form.diagnosis.trim().length < 3) {
      setFormError('Enter the diagnosis this prescription treats.');
      return;
    }
    const complete = items.filter(
      (item) => item.medicine_name.trim() && item.dosage.trim() && item.frequency.trim() && item.duration.trim()
    );
    if (complete.length === 0) {
      setFormError('Add at least one medicine with dosage, frequency and duration.');
      return;
    }

    setSubmitting(true);
    try {
      await createPrescription({
        patient_id: Number(form.patient_id),
        diagnosis: form.diagnosis.trim(),
        advice: form.advice.trim() || null,
        items: complete.map((item) => ({
          medicine_name: item.medicine_name.trim(),
          dosage: item.dosage.trim(),
          frequency: item.frequency.trim(),
          duration: item.duration.trim(),
          instructions: item.instructions.trim() || null,
        })),
      });
      setBanner('Draft prescription saved. Review it, then issue it to the patient.');
      resetForm();
      setShowForm(false);
      await load();
    } catch (apiError) {
      setFormError(apiError.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleIssue = async (prescription) => {
    try {
      await issuePrescription(prescription.id);
      setBanner(`${prescription.reference_code} issued to ${prescription.patient_name}.`);
      await load();
    } catch (apiError) {
      setBanner('');
      setLoadError(apiError.message);
    }
  };

  const handleCancel = async (prescription) => {
    if (!window.confirm(`Cancel prescription ${prescription.reference_code}?`)) return;
    try {
      await cancelPrescription(prescription.id);
      setBanner(`${prescription.reference_code} has been cancelled.`);
      await load();
    } catch (apiError) {
      setBanner('');
      setLoadError(apiError.message);
    }
  };

  if (loading) return <LoadingState message="Loading your prescriptions…" />;
  if (loadError) return <ErrorState message={loadError} onRetry={load} />;

  return (
    <>
      <div className="ju-page-header">
        <h1>Prescriptions</h1>
        <p>Write, review and issue digital prescriptions for your patients.</p>
      </div>

      <Alert tone="success">{banner}</Alert>

      <div className="ju-card">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 'var(--ju-space-3)',
            flexWrap: 'wrap',
            marginBottom: 'var(--ju-space-4)',
          }}
        >
          <h3 className="ju-card__title" style={{ margin: 0 }}>
            {showForm ? 'New Prescription' : 'Prescriptions You Have Written'}
          </h3>
          <button
            type="button"
            className="ju-btn ju-btn--primary"
            onClick={() => setShowForm((open) => !open)}
          >
            {showForm ? 'Close Editor' : 'Write Prescription'}
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleCreate} noValidate style={{ marginBottom: 'var(--ju-space-5)' }}>
            <Alert tone="error">{formError}</Alert>

            <div className="ju-form-grid">
              <FormField
                label="Patient"
                name="patient_id"
                value={form.patient_id}
                onChange={handleFormChange}
                required
                options={patients.map((patient) => ({
                  value: String(patient.patient_id),
                  label: `${patient.full_name} (${patient.university_id})`,
                }))}
                help="Only patients you have treated are listed."
              />
            </div>

            <div style={{ marginTop: 'var(--ju-space-4)' }}>
              <FormField
                label="Diagnosis"
                name="diagnosis"
                value={form.diagnosis}
                onChange={handleFormChange}
                required
                rows={2}
              />
            </div>

            <h3 className="ju-card__title" style={{ marginTop: 'var(--ju-space-5)' }}>
              Medicines
            </h3>

            {items.map((item, index) => (
              <div
                key={index}
                style={{
                  border: '1px solid var(--ju-border)',
                  borderRadius: 'var(--ju-radius)',
                  padding: 'var(--ju-space-4)',
                  marginBottom: 'var(--ju-space-3)',
                }}
              >
                <div className="ju-form-grid">
                  <FormField
                    label="Medicine Name"
                    name={`medicine_name_${index}`}
                    value={item.medicine_name}
                    onChange={(event) => handleItemChange(index, 'medicine_name', event.target.value)}
                    required
                    placeholder="Amoxicillin"
                  />
                  <FormField
                    label="Dosage"
                    name={`dosage_${index}`}
                    value={item.dosage}
                    onChange={(event) => handleItemChange(index, 'dosage', event.target.value)}
                    required
                    placeholder="500mg"
                  />
                  <FormField
                    label="Frequency"
                    name={`frequency_${index}`}
                    value={item.frequency}
                    onChange={(event) => handleItemChange(index, 'frequency', event.target.value)}
                    required
                    placeholder="1+1+1"
                  />
                  <FormField
                    label="Duration"
                    name={`duration_${index}`}
                    value={item.duration}
                    onChange={(event) => handleItemChange(index, 'duration', event.target.value)}
                    required
                    placeholder="7 days"
                  />
                  <FormField
                    label="Instructions"
                    name={`instructions_${index}`}
                    value={item.instructions}
                    onChange={(event) => handleItemChange(index, 'instructions', event.target.value)}
                    placeholder="Take after meals"
                  />
                </div>

                {items.length > 1 && (
                  <div className="ju-form-actions">
                    <button
                      type="button"
                      className="ju-btn ju-btn--ghost"
                      onClick={() => removeItem(index)}
                    >
                      Remove Medicine
                    </button>
                  </div>
                )}
              </div>
            ))}

            <button type="button" className="ju-btn ju-btn--secondary" onClick={addItem}>
              Add Another Medicine
            </button>

            <div style={{ marginTop: 'var(--ju-space-4)' }}>
              <FormField
                label="General Advice"
                name="advice"
                value={form.advice}
                onChange={handleFormChange}
                rows={2}
                placeholder="Rest, fluids, return if symptoms persist."
              />
            </div>

            <div className="ju-form-actions">
              <button type="submit" className="ju-btn ju-btn--primary" disabled={submitting}>
                {submitting ? 'Saving Draft…' : 'Save as Draft'}
              </button>
            </div>
          </form>
        )}

        {prescriptions.length === 0 ? (
          <EmptyState
            title="No prescriptions yet"
            hint="Write a prescription after completing a consultation."
          />
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--ju-space-3)' }}>
            {prescriptions.map((prescription) => (
              <li
                key={prescription.id}
                style={{
                  border: '1px solid var(--ju-border)',
                  borderRadius: 'var(--ju-radius)',
                  padding: 'var(--ju-space-4)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 'var(--ju-space-3)',
                    flexWrap: 'wrap',
                  }}
                >
                  <div>
                    <h3 style={{ margin: 0 }}>{prescription.patient_name}</h3>
                    <p className="ju-field__help" style={{ margin: '4px 0 0' }}>
                      {prescription.reference_code} · {prescription.diagnosis}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <StatusChip status={prescription.status} />
                    <button
                      type="button"
                      className="ju-btn ju-btn--secondary"
                      onClick={() => setOpenId(openId === prescription.id ? null : prescription.id)}
                    >
                      {openId === prescription.id ? 'Hide' : 'View'}
                    </button>
                    {prescription.status === 'draft' && (
                      <button
                        type="button"
                        className="ju-btn ju-btn--primary"
                        onClick={() => handleIssue(prescription)}
                      >
                        Issue to Patient
                      </button>
                    )}
                    {['draft', 'issued'].includes(prescription.status) && (
                      <button
                        type="button"
                        className="ju-btn ju-btn--danger"
                        onClick={() => handleCancel(prescription)}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>

                {openId === prescription.id && (
                  <div style={{ marginTop: 'var(--ju-space-4)' }}>
                    <MedicineTable items={prescription.items} />
                    {prescription.advice && (
                      <p style={{ marginTop: 'var(--ju-space-3)' }}>
                        <span className="ju-kpi__label">Advice</span>
                        <br />
                        {prescription.advice}
                      </p>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
