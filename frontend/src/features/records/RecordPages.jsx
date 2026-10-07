/** Health record screens: patient timeline and doctor caseload (FR-D2 to FR-D4). */
import { useCallback, useState } from 'react';

import Async from '../../components/Async';
import { Alert, EmptyState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import { api } from '../../services/apiClient';
import { todayIso } from '../../services/dates';
import { useForm, useLoad } from '../../services/hooks';

const fetchMine = () => api.get('/medical-records/my-records');
const fetchCaseload = () => api.get('/medical-records/patients');

function Timeline({ rows }) {
  if (rows.length === 0) return <EmptyState title="No medical records yet" />;
  return (
    <ul>
      {rows.map((r) => (
        <li key={r.id} className="ju-card">
          <h3>{r.title} <small>v{r.version}</small></h3>
          <p>{r.visit_date} - {r.doctor_name}</p>
          <p><strong>Diagnosis:</strong> {r.diagnosis}</p>
          {r.treatment && <p><strong>Treatment:</strong> {r.treatment}</p>}
        </li>
      ))}
    </ul>
  );
}

export function MyRecordsPage() {
  const records = useLoad(fetchMine);
  return (
    <>
      <h1>My Medical Records</h1>
      <Async state={records}>{(rows) => <Timeline rows={rows} />}</Async>
    </>
  );
}

function PatientRecord({ patientId }) {
  const load = useCallback(() => api.get(`/medical-records/patients/${patientId}`), [patientId]);
  const records = useLoad(load);
  const [form, bind, setForm] = useForm({ title: '', diagnosis: '', treatment: '' });
  const [error, setError] = useState('');

  const add = async (event) => {
    event.preventDefault();
    try {
      await api.post('/medical-records', { ...form, patient_id: patientId, visit_date: todayIso() });
      setForm({ title: '', diagnosis: '', treatment: '' });
      setError('');
      records.reload();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <>
      <form className="ju-card" onSubmit={add} noValidate>
        <Alert tone="error">{error}</Alert>
        <FormField label="Title" required {...bind('title')} />
        <FormField label="Diagnosis" required rows={2} {...bind('diagnosis')} />
        <FormField label="Treatment" rows={2} {...bind('treatment')} />
        <button type="submit" className="ju-btn ju-btn--primary">Add Clinical Entry</button>
      </form>
      <Async state={records}>{(rows) => <Timeline rows={rows} />}</Async>
    </>
  );
}

export function DoctorRecordsPage() {
  const patients = useLoad(fetchCaseload);
  const [patientId, setPatientId] = useState(null);
  return (
    <>
      <h1>Patient Records</h1>
      <Async state={patients}>
        {(rows) => rows.length === 0 ? <EmptyState title="No patients yet" hint="Patients appear after they book with you." /> : (
          rows.map((p) => (
            <button key={p.patient_id} type="button" className="ju-btn ju-btn--secondary" onClick={() => setPatientId(p.patient_id)}>
              {p.full_name} ({p.record_count})
            </button>
          ))
        )}
      </Async>
      {patientId && <PatientRecord patientId={patientId} />}
    </>
  );
}
