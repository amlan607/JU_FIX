/** Prescription screens for doctor, patient and pharmacist (FR-D1, FR-D3). */
import { useState } from 'react';

import Async from '../../components/Async';
import { Alert, EmptyState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import StatusChip from '../../components/StatusChip';
import { api } from '../../services/apiClient';
import { useForm, useLoad } from '../../services/hooks';

const fetchMine = () => api.get('/prescriptions/my-prescriptions');
const fetchWritten = () => api.get('/prescriptions/written');
const fetchQueue = () => api.get('/prescriptions/pharmacy-queue');
const fetchPatients = () => api.get('/appointments/doctor-schedule');

function Medicines({ items }) {
  return (
    <ul>
      {items.map((i) => <li key={i.id}>{i.medicine_name} {i.dosage}, {i.frequency}, {i.duration}</li>)}
    </ul>
  );
}

function PrescriptionList({ state, action }) {
  return (
    <Async state={state}>
      {(rows) => rows.length === 0 ? <EmptyState title="No prescriptions yet" /> : rows.map((p) => (
        <div key={p.id} className="ju-card">
          <h3>{p.reference_code} <StatusChip status={p.status} /></h3>
          <p>{p.patient_name} - {p.diagnosis}</p>
          <Medicines items={p.items} />
          {action?.(p)}
        </div>
      ))}
    </Async>
  );
}

export function MyPrescriptionsPage() {
  return (
    <>
      <h1>My Prescriptions</h1>
      <PrescriptionList state={useLoad(fetchMine)} />
    </>
  );
}

export function DoctorPrescriptionsPage() {
  const written = useLoad(fetchWritten);
  const patients = useLoad(fetchPatients);
  const [form, bind] = useForm({ patient_id: '', diagnosis: '', medicine_name: '', dosage: '', frequency: '', duration: '' });
  const [note, setNote] = useState({ tone: 'info', text: '' });

  const call = async (action, text) => {
    try {
      await action();
      setNote({ tone: 'success', text });
      written.reload();
    } catch (err) {
      setNote({ tone: 'error', text: err.message });
    }
  };
  const create = (event) => {
    event.preventDefault();
    const { patient_id: patientId, diagnosis, ...item } = form;
    call(() => api.post('/prescriptions', { patient_id: Number(patientId), diagnosis, items: [item] }), 'Draft saved.');
  };
  const options = Object.values(Object.fromEntries((patients.data ?? []).map((a) => [a.patient_id, { value: String(a.patient_id), label: a.patient_name }])));

  return (
    <>
      <h1>Prescriptions</h1>
      <Alert tone={note.tone}>{note.text}</Alert>
      <form className="ju-card ju-form-grid" onSubmit={create} noValidate>
        <FormField label="Patient" required options={options} help="Patients you have appointments with." {...bind('patient_id')} />
        <FormField label="Diagnosis" required {...bind('diagnosis')} />
        <FormField label="Medicine" required {...bind('medicine_name')} />
        <FormField label="Dosage" required placeholder="500mg" {...bind('dosage')} />
        <FormField label="Frequency" required placeholder="1+1+1" {...bind('frequency')} />
        <FormField label="Duration" required placeholder="7 days" {...bind('duration')} />
        <button type="submit" className="ju-btn ju-btn--primary">Save Draft</button>
      </form>
      <PrescriptionList
        state={written}
        action={(p) => p.status === 'draft' && (
          <button type="button" className="ju-btn ju-btn--primary" onClick={() => call(() => api.patch(`/prescriptions/${p.id}/issue`), 'Issued to the patient.')}>Issue</button>
        )}
      />
    </>
  );
}

export function PharmacyPage() {
  const queue = useLoad(fetchQueue);
  const [note, setNote] = useState({ tone: 'info', text: '' });
  const dispense = async (p) => {
    try {
      await api.patch(`/prescriptions/${p.id}/dispense`, { note: null });
      setNote({ tone: 'success', text: `${p.reference_code} dispensed.` });
      queue.reload();
    } catch (err) {
      setNote({ tone: 'error', text: err.message });
    }
  };
  return (
    <>
      <h1>Dispensing Queue</h1>
      <Alert tone={note.tone}>{note.text}</Alert>
      <PrescriptionList
        state={queue}
        action={(p) => p.status === 'issued' && (
          <button type="button" className="ju-btn ju-btn--primary" onClick={() => dispense(p)}>Mark Dispensed</button>
        )}
      />
    </>
  );
}
