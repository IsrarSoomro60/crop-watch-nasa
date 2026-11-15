import { ILLUSTRATIONS } from "./illustrations";

/** App sections shown in the sidebar. Plain state navigation: the project has no router. */
export const PAGES = [
  { id: "dashboard", label: "Home", icon: ILLUSTRATIONS.home },
  { id: "farm", label: "My Farm", icon: ILLUSTRATIONS.pin },
  { id: "compare", label: "Compare Crops", icon: ILLUSTRATIONS.compare },
  { id: "climate", label: "Weather", icon: ILLUSTRATIONS.climate },
  { id: "reports", label: "My Report", icon: ILLUSTRATIONS.report },
  { id: "learn", label: "Learn", icon: ILLUSTRATIONS.learn },
] as const;

export type PageId = (typeof PAGES)[number]["id"];

/** Go to a page, optionally scrolling to an element id on it once it is shown. */
export type Navigate = (page: PageId, anchor?: string) => void;
