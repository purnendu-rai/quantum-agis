/**
 * @file Reusable panel card with title, optional subtitle, and hover glow.
 */

/**
 * Dark card used to frame dashboard widgets and page sections.
 * @param {object} props - Component props.
 * @param {string} [props.title] - Card title.
 * @param {string} [props.subtitle] - Optional secondary line under the title.
 * @param {React.ReactNode} props.children - Card body content.
 * @param {string} [props.className] - Extra classes for the wrapper.
 * @returns {JSX.Element} Card container.
 */
export default function Card({ title, subtitle, children, className = '' }) {
  return (
    <section
      className={`rounded-lg border p-4 transition-shadow duration-200 hover:shadow-[0_0_14px_rgba(0,212,255,0.15)] ${className}`}
      style={{
        background: '#0d1330',
        borderColor: 'rgba(0, 212, 255, 0.2)',
      }}
    >
      {title && <h3 className="text-sm font-medium text-slate-200">{title}</h3>}
      {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
      <div className={title || subtitle ? 'mt-3' : ''}>{children}</div>
    </section>
  );
}
