/**
 * Printable certificate document (FR-F3).
 *
 * Rendered only for an approved request. The reference ID printed at the foot
 * is what a department office types into the public verification page.
 */

/**
 * Format an ISO timestamp as a readable date.
 * @param {string} value An ISO 8601 timestamp.
 * @returns {string} A readable date.
 */
function formatIssued(value) {
  return value ? new Date(value).toLocaleDateString('en-GB') : '';
}

export default function CertificateDocument({ certificate }) {
  return (
    <div
      style={{
        marginTop: 'var(--ju-space-4)',
        padding: 'var(--ju-space-5)',
        border: '2px solid var(--ju-primary)',
        borderRadius: 'var(--ju-card-radius)',
        background: 'var(--ju-surface)',
      }}
    >
      <div style={{ textAlign: 'center', marginBottom: 'var(--ju-space-5)' }}>
        <p style={{ margin: 0, fontWeight: 700, color: 'var(--ju-blue)', fontSize: '18px' }}>
          Jahangirnagar University Medical Centre
        </p>
        <p style={{ margin: '4px 0 0', fontWeight: 600 }}>Medical Certificate</p>
      </div>

      <p>
        This is to certify that <strong>{certificate.patient_name}</strong> (
        {certificate.patient_university_id}) was examined at the Jahangirnagar University Medical
        Centre and, on medical grounds, is advised leave for{' '}
        <strong>
          {certificate.leave_days} day{certificate.leave_days === 1 ? '' : 's'}
        </strong>{' '}
        from <strong>{certificate.leave_start}</strong> to{' '}
        <strong>{certificate.leave_end}</strong>.
      </p>

      {certificate.doctor_remarks && <p>Remarks: {certificate.doctor_remarks}</p>}

      <div
        style={{
          marginTop: 'var(--ju-space-5)',
          display: 'flex',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--ju-space-4)',
        }}
      >
        <div>
          <p style={{ margin: 0, fontWeight: 600 }}>{certificate.doctor_name}</p>
          <p className="ju-field__help" style={{ margin: 0 }}>
            Medical Officer · issued {formatIssued(certificate.decided_at)}
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <p className="ju-kpi__label" style={{ margin: 0 }}>
            Reference ID
          </p>
          <p style={{ margin: 0, fontWeight: 700, letterSpacing: '0.5px' }}>
            {certificate.reference_id}
          </p>
        </div>
      </div>

      <p className="ju-field__help" style={{ marginTop: 'var(--ju-space-4)' }}>
        This certificate is digitally signed. Verify it at /verify-certificate using the reference
        ID above.
      </p>

      <div className="ju-form-actions">
        <button type="button" className="ju-btn ju-btn--secondary" onClick={() => window.print()}>
          Print or Save as PDF
        </button>
      </div>
    </div>
  );
}
