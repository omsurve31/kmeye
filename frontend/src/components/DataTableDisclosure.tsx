type DataTableDisclosureProps = {
  caption: string
  columns: string[]
  rows: string[][]
}

// Every chart offers its numbers as a table, for screen readers and for anyone who wants exact values.
export function DataTableDisclosure({ caption, columns, rows }: DataTableDisclosureProps) {
  return (
    <details className="data-table">
      <summary>View data as a table</summary>
      <div className="data-table__scroll">
        <table>
          <caption className="visually-hidden">{caption}</caption>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column} scope="col">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.join('|')}>
                {row.map((cell, index) => (
                  <td key={columns[index]}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}
