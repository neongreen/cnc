export default function MaturityTable({ tableContent }: { tableContent: string }) {
  return <div dangerouslySetInnerHTML={{ __html: tableContent }} />
}
