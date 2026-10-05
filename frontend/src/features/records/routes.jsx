/**
 * Route declarations for the Electronic Health Record feature (FR-D2 to FR-D5).
 *
 * Owner: Ziad Muhammad Tahzeeb Rahman (375).
 */
import DoctorPatientsPage from './DoctorPatientsPage';
import MyRecordsPage from './MyRecordsPage';
import PatientRecordPage from './PatientRecordPage';

export default [
  { path: '/medical-records', element: <MyRecordsPage />, roles: ['student', 'faculty'] },
  { path: '/doctor/patients', element: <DoctorPatientsPage />, roles: ['doctor'] },
  { path: '/doctor/patients/:patientId', element: <PatientRecordPage />, roles: ['doctor'] },
];
