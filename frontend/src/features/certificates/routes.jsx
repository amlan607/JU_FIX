/**
 * Route declarations for medical certificates and sick leave (FR-F).
 *
 * Owner: Shadman Rahman (376).
 */
import CertificateReviewPage from './CertificateReviewPage';
import MyCertificatesPage from './MyCertificatesPage';
import RequestCertificatePage from './RequestCertificatePage';
import VerifyCertificatePage from './VerifyCertificatePage';

export default [
  { path: '/certificates', element: <MyCertificatesPage />, roles: ['student', 'faculty'] },
  { path: '/certificates/request', element: <RequestCertificatePage />, roles: ['student', 'faculty'] },
  { path: '/doctor/certificate-requests', element: <CertificateReviewPage />, roles: ['doctor'] },
  { path: '/verify-certificate', element: <VerifyCertificatePage />, layout: 'public' },
];
