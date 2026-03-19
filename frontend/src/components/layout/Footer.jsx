import './Footer.css'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-eu">
        <img
          src="https://aideaacademy.eu/demo/wp-content/uploads/2026/03/EN-Co-funded-by-the-EU_PANTONE-300x63-1.jpg"
          alt="Co-funded by the European Union"
          className="footer-eu-logo"
        />
        <p className="footer-eu-text">
          Funded by the European Union. Views and opinions expressed are however those of the
          author(s) only and do not necessarily reflect those of the European Union or the European
          Education and Culture Executive Agency (EACEA).
        </p>
      </div>
      <div className="footer-bottom">
        <span>© {new Date().getFullYear()} AIDEA by ICCS</span>
        <a href="https://aideaacademy.eu/demo/" target="_blank" rel="noopener noreferrer">
          aideaacademy.eu
        </a>
      </div>
    </footer>
  )
}
