/**
 * Route declarations for digital prescription management (FR-D1, FR-D3).
 *
 * Owner: Md Sher Ali (364).
 */
import MyPrescriptionsPage from './MyPrescriptionsPage';
import PharmacyQueuePage from './PharmacyQueuePage';
import PrescriptionEditorPage from './PrescriptionEditorPage';

export default [
  { path: '/prescriptions', element: <MyPrescriptionsPage />, roles: ['student', 'faculty'] },
  { path: '/doctor/prescriptions', element: <PrescriptionEditorPage />, roles: ['doctor'] },
  { path: '/pharmacy/prescriptions', element: <PharmacyQueuePage />, roles: ['pharmacist'] },
];
