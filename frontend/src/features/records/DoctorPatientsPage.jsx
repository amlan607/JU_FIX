/**
 * Doctor patient list (FR-D4).
 *
 * Route: `/doctor/patients`. Lists only the patients the signed in doctor is
 * authorised to open, which the backend derives from their own caseload.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import { fetchAuthorisedPatients } from './recordApi';
import { formatVisitDate } from './recordTypes';

export default function DoctorPatientsPage() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPatients(await fetchAuthorisedPatients());
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const term = search.trim().toLowerCase();
  const visible = term
    ? patients.filter(
        (patient) =>
          patient.full_name.toLowerCase().includes(term) ||
          patient.university_id.toLowerCase().includes(term)
      )
    : patients;

  if (loading) return <LoadingState message="Loading your patient list…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <>
      <div className="ju-page-header">
        <h1>Patient Records</h1>
        <p>Patients you have treated or are scheduled to treat.</p>
      </div>

      <div className="ju-card">
        <div style={{ maxWidth: '320px', marginBottom: 'var(--ju-space-4)' }}>
          <FormField
            label="Search Patients"
            name="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Name or university ID"
          />
        </div>

        {visible.length === 0 ? (
          <EmptyState
            title="No patients to show"
            hint="A patient appears here once they book a consultation with you."
          />
        ) : (
          <div className="ju-table-wrap">
            <table className="ju-table">
              <caption className="ju-field__help" style={{ textAlign: 'left', paddingBottom: '8px' }}>
                Patients whose records you are authorised to open.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Patient</th>
                  <th scope="col">University ID</th>
                  <th scope="col">Department</th>
                  <th scope="col">Records</th>
                  <th scope="col">Last Visit</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((patient) => (
                  <tr key={patient.patient_id}>
                    <td>
                      <strong>{patient.full_name}</strong>
                    </td>
                    <td>{patient.university_id}</td>
                    <td>{patient.department ?? '—'}</td>
                    <td>{patient.record_count}</td>
                    <td>{patient.last_visit ? formatVisitDate(patient.last_visit) : 'No visits yet'}</td>
                    <td>
                      <Link
                        to={`/doctor/patients/${patient.patient_id}`}
                        className="ju-btn ju-btn--secondary"
                      >
                        Open Record
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
