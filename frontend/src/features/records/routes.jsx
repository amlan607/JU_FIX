/** Route declarations for Electronic Health Records. Owner: Ziad Muhammad Tahzeeb Rahman (375). */
import { DoctorRecordsPage, MyRecordsPage } from './RecordPages';

export default [
  { path: '/medical-records', element: <MyRecordsPage />, roles: ['student', 'faculty'] },
  { path: '/doctor/patients', element: <DoctorRecordsPage />, roles: ['doctor'] },
];
