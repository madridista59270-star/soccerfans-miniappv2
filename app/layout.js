import "./globals.css";

export const metadata = {
  title: "Soccer Fans",
  description: "Boutique Telegram de maillots"
};

export default function RootLayout({ children }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
