import { useTable } from "react-table";

export default function Table({ columns, data, title }) {
    // const memorisedColumns = React.useMemo(columns, []);
    // const memorisedData = React.useMemo(data, []);
    const tableInstance = useTable({ columns, data });

    const { getTableProps, getTableBodyProps, headerGroups, rows, prepareRow } =
        tableInstance;

    return (
        <table {...getTableProps()} style={{ border: "solid 1px blue" }}>
            <caption className="table-header">{title}</caption>
            <thead>
                {headerGroups.map((headerGroup) => {
                    return (
                        <tr {...headerGroup.getHeaderGroupProps()}>
                            {headerGroup.headers.map((column) => {
                                return (
                                    <th {...column.getHeaderProps()}>
                                        {column.render("Header")}
                                    </th>
                                );
                            })}
                        </tr>
                    );
                })}
            </thead>

            <tbody {...getTableBodyProps()}>
                {rows.map((row) => {
                    prepareRow(row);
                    return (
                        <tr {...row.getRowProps()}>
                            {row.cells.map((cell) => {
                                let classes = []
                                if (cell.column.id === 'row_name') {
                                    classes.push('row-name')
                                }
                                return (
                                    <td className={classes} {...cell.getCellProps()}>
                                        {cell.render("Cell")}
                                    </td>
                                );
                            })}
                        </tr>
                    );
                })}
            </tbody>
        </table>
    );
}
