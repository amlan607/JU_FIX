/**
 * Read only medicine table shared by every prescription screen.
 *
 * The doctor, the patient and the pharmacist all see the medicine list in the
 * same layout, which removes any doubt about what was prescribed (DRY).
 */
export default function MedicineTable({ items }) {
  if (!items || items.length === 0) {
    return <p className="ju-field__help">No medicines have been added yet.</p>;
  }

  return (
    <div className="ju-table-wrap">
      <table className="ju-table">
        <caption className="ju-field__help" style={{ textAlign: 'left', paddingBottom: '8px' }}>
          Prescribed medicines with dosage, frequency and duration.
        </caption>
        <thead>
          <tr>
            <th scope="col">Medicine</th>
            <th scope="col">Dosage</th>
            <th scope="col">Frequency</th>
            <th scope="col">Duration</th>
            <th scope="col">Instructions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={item.id ?? index}>
              <td>
                <strong>{item.medicine_name}</strong>
              </td>
              <td>{item.dosage}</td>
              <td>{item.frequency}</td>
              <td>{item.duration}</td>
              <td>{item.instructions || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
