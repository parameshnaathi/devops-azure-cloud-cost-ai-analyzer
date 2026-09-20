export default function ResourceTable({ resources = [] }) {
  if (resources.length === 0) {
    return null;
  }

  return (
    <table className="resource-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Location</th>
          <th>SKU</th>
        </tr>
      </thead>
      <tbody>
        {resources.map((resource, index) => (
          <tr key={`${resource.id || resource.name}-${index}`}>
            <td>{resource.name}</td>
            <td>{resource.type}</td>
            <td>{resource.location}</td>
            <td>{resource.sku?.name || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
