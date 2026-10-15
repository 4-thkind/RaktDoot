import Link from "next/link";

export default function NotFound() {
  return (
    <div className="narrow" style={{ paddingTop: 48 }}>
      <h1 className="h1">This page does not exist.</h1>
      <p className="muted">If you need blood for a patient, start here.</p>
      <Link className="btn btn-primary" href="/find">Find blood now</Link>
    </div>
  );
}
