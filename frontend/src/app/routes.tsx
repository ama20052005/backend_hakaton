import { createBrowserRouter } from "react-router";

import Root from "./components/Root";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Root,
    children: [
      {
        index: true,
        lazy: async () => ({
          Component: (await import("./components/Landing")).default,
        }),
      },
      {
        path: "analytics",
        lazy: async () => ({
          Component: (await import("./components/Analytics")).default,
        }),
      },
      {
        path: "report",
        lazy: async () => ({
          Component: (await import("./components/Report")).default,
        }),
      },
    ],
  },
]);
