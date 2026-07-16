export function AvatarPanel() {
  return (
    <aside className="avatar-panel" aria-labelledby="avatar-title">
      <div className="avatar-visual" aria-hidden="true">
        <div className="avatar-orbit avatar-orbit--outer" />
        <div className="avatar-orbit avatar-orbit--inner" />
        <div className="avatar-core">AI</div>
      </div>

      <div className="avatar-copy">
        <div className="status-line">
          <span className="status-dot" aria-hidden="true" />
          Text coaching available
        </div>
        <h2 id="avatar-title">Your coaching space</h2>
        <p>
          A calm place to reflect, clarify your thoughts, and explore practical
          next steps.
        </p>
      </div>

      <div className="placeholder-card">
        <span className="placeholder-icon" aria-hidden="true">
          ◌
        </span>
        <div>
          <strong>Talking avatar</strong>
          <span>Coming in a future version</span>
        </div>
      </div>
    </aside>
  );
}
