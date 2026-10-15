"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Group } from "@/lib/api";
import { mapLink, show } from "@/lib/blood";
import { useAgo, useLang } from "@/lib/i18n";

type Shared = {
  status: string;
  patient_group: Group;
  group_confirmed: boolean;
  compatible: Group[];
  units: number;
  patient_age: number;
  patient_gender: "M" | "F" | "O";
  hospital: { name: string; address: string | null; lat: number; lng: number };
  created_at: string;
  closed_at: string | null;
  connected: number;
  target: number;
};

export default function SharedRequest() {
  const { slug } = useParams<{ slug: string }>();
  const { t } = useLang();
  const ago = useAgo();
  const [data, setData] = useState<Shared | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Shared>(`/api/share/${slug}`).then(setData).catch((e) => setError(e.message));
  }, [slug]);

  if (error) return <div className="narrow" style={{ paddingTop: 32 }}><p className="note">{error}</p></div>;
  if (!data) return null;
  const closed = !["dispatching", "matched", "needs_public_share", "open"].includes(data.status);

  return (
    <div className="narrow" style={{ paddingTop: 32 }}>
      {closed ? (
        <p className="note neutral">{t("share_closed")}</p>
      ) : (
        <p className="muted small" style={{ margin: 0 }}>{t("share_posted", { when: ago(data.created_at) })}</p>
      )}
      <h1 className="display" style={{ fontSize: "clamp(64px, 20vw, 120px)", marginTop: 10 }}>{show(data.patient_group)}</h1>
      <p className="h2" style={{ marginTop: 4 }}>
        {t("share_needed", { units: data.units })}
        {!data.group_confirmed && <span className="small muted"> ({t("share_unconfirmed")})</span>}
      </p>
      <dl className="facts" style={{ marginTop: 24 }}>
        <div><dt className="muted">{t("share_receive")}</dt><dd className="num" style={{ margin: 0, fontWeight: 600 }}>{data.compatible.map(show).join(", ")}</dd></div>
        <div><dt className="muted">{t("hospital")}</dt><dd style={{ margin: 0 }}>
          <a href={mapLink(data.hospital.lat, data.hospital.lng)} target="_blank" rel="noreferrer">{data.hospital.name}</a>
          {data.hospital.address && <div className="small muted">{data.hospital.address}</div>}
        </dd></div>
        <div><dt className="muted">{t("patient")}</dt><dd className="num" style={{ margin: 0 }}>{data.patient_age}, {t(data.patient_gender === "M" ? "male" : data.patient_gender === "F" ? "female" : "other")}</dd></div>
      </dl>
      {!closed && (
        <div className="sheet stack" style={{ marginTop: 24 }}>
          <p style={{ margin: 0 }}>{t("share_how")}</p>
          <Link href="/donate" className="btn btn-primary btn-block">{t("register_donor")}</Link>
        </div>
      )}
      <p className="tiny muted" style={{ marginTop: 20 }}>{t("trust_1")}</p>
    </div>
  );
}
