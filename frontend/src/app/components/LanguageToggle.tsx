import { useLanguage } from "../lib/language";

export default function LanguageToggle() {
  const { language, setLanguage } = useLanguage();

  return (
    <div className="inline-flex border border-foreground/10 bg-white">
      {[
        { id: "ru", label: "RU" },
        { id: "en", label: "EN" },
      ].map((item) => {
        const active = language === item.id;

        return (
          <button
            key={item.id}
            type="button"
            onClick={() => setLanguage(item.id as "ru" | "en")}
            className={`min-w-12 px-3 py-2 text-xs font-semibold tracking-[0.18em] transition ${
              active
                ? "bg-foreground text-background"
                : "text-foreground/55 hover:bg-secondary"
            }`}
            aria-pressed={active}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
