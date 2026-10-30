import { defineConfig } from "vite"; import react from "@vitejs/plugin-react"; import { VitePWA } from "vite-plugin-pwa";
export default defineConfig({ plugins: [react(), VitePWA({ registerType: "autoUpdate", manifest: { name: "TUVA", short_name: "TUVA",
  theme_color: "#061743", background_color: "#061743", display: "standalone", start_url: "/",
  icons: [
    { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
    { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any maskable" },
  ] } })] });
