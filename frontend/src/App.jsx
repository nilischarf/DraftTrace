import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  Loader2,
  ShieldCheck,
  Unplug,
} from "lucide-react";

import { createReport, getGoogleStatus, probeRevisionSnapshots, startGoogleAuth } from "./api";

const initialForm = {
  student_name: "Maya Cohen",
  assignment_name: "Modern History Essay",
  document_url: "https://docs.google.com/document/d/example/edit",
};

function statusLabel(status) {
  if (status === "low_concern") return "Low concern";
  if (status === "insufficient_evidence") return "Insufficient evidence";
  return "Needs review";
}

function App() {
  const [form, setForm] = useState(initialForm);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [googleStatus, setGoogleStatus] = useState(null);
  const [snapshotProbe, setSnapshotProbe] = useState(null);
  const [isProbingSnapshots, setIsProbingSnapshots] = useState(false);

  useEffect(() => {
    refreshGoogleStatus();
  }, []);

  async function refreshGoogleStatus() {
    try {
      setGoogleStatus(await getGoogleStatus());
    } catch (nextError) {
      setError(nextError.message);
    }
  }

  async function handleConnectGoogle() {
    setError("");

    try {
      const { authorization_url } = await startGoogleAuth();
      window.location.href = authorization_url;
    } catch (nextError) {
      setError(nextError.message);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (!googleStatus?.connected) {
      setError("Connect Google before generating a real document report.");
      return;
    }

    setIsLoading(true);

    try {
      const nextReport = await createReport(form);
      setReport(nextReport);
    } catch (nextError) {
      setError(nextError.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSnapshotProbe() {
    setError("");

    if (!googleStatus?.connected) {
      setError("Connect Google before testing revision snapshots.");
      return;
    }

    setIsProbingSnapshots(true);

    try {
      const nextProbe = await probeRevisionSnapshots({
        document_url: form.document_url,
        max_revisions: 8,
      });
      setSnapshotProbe(nextProbe);
    } catch (nextError) {
      setError(nextError.message);
    } finally {
      setIsProbingSnapshots(false);
    }
  }

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <main className="app-shell">
      <section className="intro">
        <div>
          <p className="eyebrow">DraftTrace prototype</p>
          <h1>Review the writing process, not just the final essay.</h1>
          <p className="lede">
            Submit a Google Doc and generate an evidence-based authorship report for teachers.
          </p>
        </div>
        <div className="principle">
          <ShieldCheck size={22} />
          <span>Flags are review prompts, not accusations.</span>
        </div>
      </section>

      <section className="workspace">
        <form className="submit-panel" onSubmit={handleSubmit}>
          <div className="panel-heading">
            <FileText size={22} />
            <h2>Student Submission</h2>
          </div>

          <div className="google-box">
            <div>
              <strong>Google Docs access</strong>
              <p>{googleConnectionMessage(googleStatus)}</p>
            </div>
            <button
              className="secondary-button"
              disabled={!googleStatus?.configured}
              type="button"
              onClick={handleConnectGoogle}
            >
              <Unplug size={17} />
              {googleStatus?.connected ? "Reconnect" : "Connect Google"}
            </button>
          </div>

          <label>
            Student name
            <input
              value={form.student_name}
              onChange={(event) => updateField("student_name", event.target.value)}
              placeholder="Student name"
            />
          </label>

          <label>
            Assignment
            <input
              value={form.assignment_name}
              onChange={(event) => updateField("assignment_name", event.target.value)}
              placeholder="Assignment name"
            />
          </label>

          <label>
            Google Doc URL
            <input
              value={form.document_url}
              onChange={(event) => updateField("document_url", event.target.value)}
              placeholder="https://docs.google.com/document/d/..."
            />
          </label>

          <button type="submit" disabled={isLoading}>
            {isLoading ? <Loader2 className="spin" size={18} /> : <CheckCircle2 size={18} />}
            Generate report
          </button>

          <button
            className="secondary-button"
            type="button"
            disabled={isProbingSnapshots}
            onClick={handleSnapshotProbe}
          >
            {isProbingSnapshots ? <Loader2 className="spin" size={18} /> : <FileText size={18} />}
            Test revision snapshots
          </button>

          {error ? <p className="error">{error}</p> : null}
        </form>

        <section className="report-panel">
          {snapshotProbe ? <SnapshotProbe probe={snapshotProbe} /> : null}
          {report ? <Report report={report} /> : <EmptyReport />}
        </section>
      </section>
    </main>
  );
}

function SnapshotProbe({ probe }) {
  return (
    <div className="snapshot-probe">
      <div className="report-header">
        <div>
          <p className="eyebrow">Revision snapshot spike</p>
          <h2>{probe.document.name}</h2>
          <p>{probe.note}</p>
        </div>
        <div className={`status ${probe.snapshot_available ? "low_concern" : "needs_review"}`}>
          {probe.snapshot_available ? "Snapshots found" : "No snapshots"}
        </div>
      </div>

      <div className="metrics-grid compact">
        <div className="metric">
          <span>total revisions</span>
          <strong>{probe.revision_count}</strong>
        </div>
        <div className="metric">
          <span>sampled revisions</span>
          <strong>{probe.sampled_revision_count}</strong>
        </div>
        <div className="metric">
          <span>successful snapshots</span>
          <strong>{probe.successful_snapshot_count}</strong>
        </div>
        <div className="metric">
          <span>largest word delta</span>
          <strong>{probe.largest_word_count_delta}</strong>
        </div>
      </div>

      <ol className="snapshot-list">
        {probe.snapshots.map((snapshot) => (
          <li key={snapshot.revision_id}>
            <strong>Revision {snapshot.revision_id}</strong>
            <span>{snapshot.modified_time ?? "Unknown time"}</span>
            <p>
              {snapshot.available
                ? `${snapshot.word_count} words, ${snapshot.character_count} characters`
                : snapshot.reason}
            </p>
          </li>
        ))}
      </ol>
    </div>
  );
}

function googleConnectionMessage(status) {
  if (!status) return "Checking connection...";
  if (!status.configured) return "Add Google OAuth credentials in backend/.env.";
  if (!status.connected) return "Ready to connect a Google account.";
  return "Connected. You can generate a report from a real Google Doc URL.";
}

function EmptyReport() {
  return (
    <div className="empty-state">
      <AlertTriangle size={28} />
      <h2>No report yet</h2>
      <p>Generate a sample report to see the teacher-facing review experience.</p>
    </div>
  );
}

function Report({ report }) {
  return (
    <div>
      <div className="report-header">
        <div>
          <p className="eyebrow">Authorship report</p>
          <h2>{report.assignment_name}</h2>
          <p>{report.student_name}</p>
        </div>
        <div className={`status ${report.status}`}>{statusLabel(report.status)}</div>
      </div>

      <div className="score-row">
        <div className="score">
          <strong>{report.confidence_score}</strong>
          <span>review score</span>
        </div>
        <p>{report.summary}</p>
      </div>

      <div className="metrics-grid">
        {Object.entries(report.metrics).map(([key, value]) => (
          <div className="metric" key={key}>
            <span>{key.replaceAll("_", " ")}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>

      <h3>Timeline</h3>
      <ol className="timeline">
        {report.timeline.map((event) => (
          <li className={event.severity} key={`${event.time}-${event.label}`}>
            <time>{event.time}</time>
            <div>
              <strong>{event.label}</strong>
              <p>{event.detail}</p>
            </div>
          </li>
        ))}
      </ol>

      <div className="teacher-note">
        <strong>Teacher note</strong>
        <p>{report.teacher_note}</p>
      </div>
    </div>
  );
}

export default App;
