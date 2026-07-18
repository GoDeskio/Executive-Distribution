import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import api from "@/lib/api";

function getSessionId() {
  let id = localStorage.getItem("ed_session");
  if (!id) {
    id = "s_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("ed_session", id);
  }
  return id;
}

export function useTracking() {
  const location = useLocation();

  useEffect(() => {
    // Do not track admin routes
    if (location.pathname.startsWith("/admin") || location.pathname === "/login") return;
    const session_id = getSessionId();
    const path = location.pathname;

    api.post("/track", {
      session_id,
      path,
      event_type: "pageview",
      referrer: document.referrer || "",
      viewport_w: window.innerWidth,
      viewport_h: window.innerHeight,
    }).catch(() => {});

    let lastClick = 0;
    const onClick = (e) => {
      const now = Date.now();
      if (now - lastClick < 150) return;
      lastClick = now;
      const x = +(e.clientX / window.innerWidth).toFixed(4);
      const doc = document.documentElement;
      const y = +((e.clientY + window.scrollY) / doc.scrollHeight).toFixed(4);
      api.post("/track", {
        session_id, path, event_type: "click", x, y,
        viewport_w: window.innerWidth, viewport_h: window.innerHeight,
      }).catch(() => {});
    };

    let maxScroll = 0;
    let scrollTimer = null;
    const onScroll = () => {
      const doc = document.documentElement;
      const depth = (window.scrollY + window.innerHeight) / doc.scrollHeight;
      if (depth > maxScroll) maxScroll = depth;
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(() => {
        api.post("/track", {
          session_id, path, event_type: "scroll",
          scroll_depth: +Math.min(maxScroll, 1).toFixed(3),
        }).catch(() => {});
      }, 800);
    };

    window.addEventListener("click", onClick);
    window.addEventListener("scroll", onScroll);
    return () => {
      window.removeEventListener("click", onClick);
      window.removeEventListener("scroll", onScroll);
      clearTimeout(scrollTimer);
    };
  }, [location.pathname]);
}
