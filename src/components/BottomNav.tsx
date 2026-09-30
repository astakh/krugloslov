import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Home, BookOpen, User } from "lucide-react";

/**
 * Routes where the bottom navigation should be hidden.
 */
const HIDDEN_ROUTES_PREFIXES = ["/lesson"];

function shouldHideNav(pathname: string): boolean {
  return HIDDEN_ROUTES_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

const navItems = [
  { to: "/", icon: Home, label: "Главная" },
  { to: "/dictionary", icon: BookOpen, label: "Словарь" },
  { to: "/profile", icon: User, label: "Профиль" },
];

const BottomNav: React.FC = () => {
  const location = useLocation();

  if (shouldHideNav(location.pathname)) {
    return null;
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
      <div className="max-w-[640px] mx-auto flex items-center justify-around h-16">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-1 px-3 py-2 rounded-lg transition-colors ${
                isActive
                  ? "text-indigo-600"
                  : "text-gray-500 hover:text-gray-700"
              }`
            }
          >
            <Icon size={22} />
            <span className="text-xs font-medium">{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
};

export default BottomNav;
