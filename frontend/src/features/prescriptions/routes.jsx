/** Route declarations for digital prescriptions. Owner: Md Sher Ali (364). */
import { DoctorPrescriptionsPage, MyPrescriptionsPage, PharmacyPage } from './PrescriptionPages';

export default [
  { path: '/prescriptions', element: <MyPrescriptionsPage />, roles: ['student', 'faculty'] },
  { path: '/doctor/prescriptions', element: <DoctorPrescriptionsPage />, roles: ['doctor'] },
  { path: '/pharmacy/prescriptions', element: <PharmacyPage />, roles: ['pharmacist'] },
];
