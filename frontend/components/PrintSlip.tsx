"use client";

import type { Snapshot } from "@/lib/api";
import { show } from "@/lib/blood";

/** Formal blood requisition & donor arrangement slip, laid out like Indian hospital blood-bank requisition forms
 * (patient identity, clinical details, product requested, blood-centre-only section, signatures).
 * Hidden on screen; it is the only thing printed (see .print-doc in globals.css). */
const COMPONENT: Record<string, string> = {
  prbc: "Packed Red Blood Cells (PRBC)", platelets: "Platelet Concentrate (RDP/SDP)", plasma: "Fresh Frozen Plasma (FFP)", whole_blood: "Whole Blood",
};
const SEX: Record<string, string> = { M: "Male", F: "Female", O: "Other" };

export function PrintSlip({ snap }: { snap: Snapshot }) {
  const ref = `RD-${snap.id.slice(0, 8).toUpperCase()}`;
  const issued = new Date().toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
  const created = new Date(snap.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
  const donors = snap.donors.filter((d) => ["connected", "donated", "accepted"].includes(d.status));
  const blank = <span className="pd-blank" />;
  return (
    <section className="print-doc" aria-hidden="true">
      <header className="pd-head">
        <div>
          <div className="pd-brand">RAKT DOOT · रक्त दूत</div>
          <div className="pd-sub">Emergency blood coordination service</div>
        </div>
        <div className="pd-meta">
          <div>Ref. No.: <b>{ref}</b></div>
          <div>Request raised: {created}</div>
          <div>Printed: {issued}</div>
        </div>
      </header>
      <h1 className="pd-title">BLOOD REQUISITION &amp; DONOR ARRANGEMENT SLIP</h1>
      <p className="pd-to">To: The Medical Officer In-charge, Blood Centre, <b>{snap.hospital.name}</b>{snap.hospital.address ? `, ${snap.hospital.address}` : ""}</p>

      <h2>A. Patient details</h2>
      <table className="pd-grid"><tbody>
        <tr><th>Patient name</th><td>{blank}</td><th>UHID / MRD / IPD No.</th><td>{blank}</td></tr>
        <tr><th>Age</th><td>{snap.patient_age ? `${snap.patient_age} years` : blank}</td><th>Sex</th><td>{SEX[snap.patient_gender] ?? blank}</td></tr>
        <tr><th>Ward / Bed No.</th><td>{blank}</td><th>Unit / Treating doctor</th><td>{blank}</td></tr>
        <tr><th>Blood group</th><td><b>{show(snap.patient_group)}</b>{snap.group_confirmed ? "" : " (not yet confirmed; to be grouped at blood centre)"}</td>
          <th>Hospital verification</th><td>{snap.hospital.verified ? `Verified (${snap.hospital.check?.evidence?.[0]?.source ?? "directory"})` : "Not verified"}</td></tr>
      </tbody></table>

      <h2>B. Clinical details (to be filled by treating doctor)</h2>
      <table className="pd-grid"><tbody>
        <tr><th>Clinical diagnosis</th><td colSpan={3}>{blank}</td></tr>
        <tr><th>Indication for transfusion</th><td colSpan={3}>{blank}</td></tr>
        <tr><th>Hb (g/dL)</th><td>{blank}</td><th>Platelet count</th><td>{blank}</td></tr>
        <tr><th>Previous transfusion</th><td>Yes / No</td><th>Previous reaction</th><td>Yes / No</td></tr>
        <tr><th>Pregnancy (if female)</th><td>Yes / No / NA</td><th>Urgency</th><td>Routine / Planned / <b>Emergency</b></td></tr>
      </tbody></table>

      <h2>C. Blood / component requested</h2>
      <table className="pd-grid"><tbody>
        <tr><th>Component</th><td>{COMPONENT[snap.component] ?? snap.component}</td><th>No. of units</th><td><b>{snap.units}</b></td></tr>
        <tr><th>Compatible donor groups</th><td colSpan={3}>{snap.compatible.map(show).join(", ")} <span className="pd-note">(cross-match mandatory before issue)</span></td></tr>
      </tbody></table>

      <h2>D. Voluntary donors arranged through Rakt Doot</h2>
      <table className="pd-list">
        <thead><tr><th>#</th><th>Donor</th><th>Group</th><th>Distance</th><th>Status</th><th>Contact</th><th>Bag No. (blood centre)</th></tr></thead>
        <tbody>
          {donors.length === 0 && <tr><td colSpan={7} className="pd-center">No donor confirmed at the time of printing. Live status: {snap.share_url}</td></tr>}
          {donors.map((d, i) => (
            <tr key={d.id}><td>{i + 1}</td><td>{d.name}</td><td>{show(d.group)}</td><td>{d.distance_km} km</td>
              <td>{d.status === "accepted" ? "Screening" : d.status === "connected" ? "Coming to donate" : d.status === "donated" ? "Donated" : d.status}</td>
              <td>{d.phone ? `+${d.phone}` : "Shared on confirmation"}</td><td>{blank}</td></tr>
          ))}
        </tbody>
      </table>
      <p className="pd-note">Donors are voluntary and unpaid. All donors are pre-screened by questionnaire only; final donor selection, grouping, TTI screening and cross-matching are the responsibility of the blood centre as per NBTC / Drugs &amp; Cosmetics Rules.</p>

      <h2>E. Requested by</h2>
      <table className="pd-grid"><tbody>
        <tr><th>Patient attendant</th><td>{snap.requester_name}</td><th>Relation to patient</th><td>{blank}</td></tr>
        <tr><th>Signature of attendant</th><td>{blank}</td><th>Signature &amp; stamp of treating doctor</th><td className="pd-sign">{blank}</td></tr>
      </tbody></table>

      <h2>F. For blood centre use only</h2>
      <table className="pd-grid"><tbody>
        <tr><th>Sample received (date/time)</th><td>{blank}</td><th>Patient group (ABO / Rh)</th><td>{blank}</td></tr>
        <tr><th>Cross-match method</th><td>Saline / AHG / Gel card</td><th>Cross-match result</th><td>Compatible / Incompatible</td></tr>
        <tr><th>Units issued</th><td>{blank}</td><th>Bag No(s).</th><td>{blank}</td></tr>
        <tr><th>Technologist signature</th><td className="pd-sign">{blank}</td><th>Medical Officer signature &amp; stamp</th><td className="pd-sign">{blank}</td></tr>
      </tbody></table>

      <footer className="pd-foot">
        Generated by Rakt Doot ({ref}). This slip supports, and does not replace, the hospital&apos;s own blood requisition form.
        No charge is payable to donors; sale of blood is prohibited in India. Live status: {snap.share_url}
      </footer>
    </section>
  );
}
