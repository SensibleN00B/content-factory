import { NavLink } from "react-router-dom";

type NavItem = {
  to: string;
  label: string;
};

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard" },
  { to: "/settings", label: "Settings" },
  { to: "/runs", label: "Run Console" },
  { to: "/shortlist", label: "Shortlist" },
];

export function AppNav() {
  return (
    <nav aria-label="Primary" className="app-nav">
      <div className="app-nav-brand">
        <p className="app-nav-kicker">Content Factory</p>
        <h1>Discovery Desk</h1>
      </div>
      <div className="app-nav-links">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              isActive ? "app-nav-link app-nav-link-active" : "app-nav-link"
            }
          >
            {item.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
