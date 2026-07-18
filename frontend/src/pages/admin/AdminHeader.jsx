export function AdminHeader({ title, subtitle, children }) {
  return (
    <div className="h-20 border-b border-[#27272A] flex items-center justify-between px-8 sticky top-0 bg-[#0A0A0B]/85 backdrop-blur-xl z-30">
      <div>
        <h1 className="font-display text-xl leading-tight">{title}</h1>
        {subtitle && <p className="text-xs text-[#71717A] mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">{children}</div>
    </div>
  );
}
