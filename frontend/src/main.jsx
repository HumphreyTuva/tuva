import React from "react"; import { createRoot } from "react-dom/client"; import { GoogleOAuthProvider } from "@react-oauth/google";
import App from "./App.jsx"; import "./styles.css";
const app = <App />;
createRoot(document.getElementById("root")).render(import.meta.env.VITE_GOOGLE_CLIENT_ID
  ? <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>{app}</GoogleOAuthProvider>
  : app);
