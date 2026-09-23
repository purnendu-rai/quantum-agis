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
    <section className={`glass glass-hover rounded-xl p-4.5 ${className}`}>
      {title && <h3 className="text-base font-semibold tracking-tight text-white">{title}</h3>}
      {subtitle && <p className="mt-1 text-xs font-normal leading-normal text-slate-300">{subtitle}</p>}
      <div className={title || subtitle ? 'mt-3.5' : ''}>{children}</div>
    </section>
  );
}
