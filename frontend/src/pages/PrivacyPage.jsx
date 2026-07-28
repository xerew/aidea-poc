import { useTranslation } from 'react-i18next'
import LegalLayout from '../components/LegalLayout'

export default function PrivacyPage() {
  const { t } = useTranslation()
  return (
    <LegalLayout title={t('legal.privacyTitle')}>
      <p>
        This Privacy Policy explains how the AIDEA platform, operated by the Information Management
        Unit of the Institute of Communication and Computer Systems (ICCS), collects and uses your
        personal data. We process personal data in accordance with the EU General Data Protection
        Regulation (GDPR).
      </p>

      <h2>1. Who we are</h2>
      <p>
        The data controller is the Information Management Unit (ICCS). You can contact us at{' '}
        <a href="mailto:info@aidea-hub.eu">info@aidea-hub.eu</a> or via{' '}
        <a href="https://imu.ntua.gr/wp/" target="_blank" rel="noreferrer">imu.ntua.gr</a>.
      </p>

      <h2>2. What data we collect</h2>
      <ul>
        <li><strong>Account information:</strong> your name, username, and email address.</li>
        <li><strong>Profile information:</strong> optional details such as gender, country, school, subject, language and biography.</li>
        <li><strong>Learning activity:</strong> enrolments, progress, quiz results, assignment submissions and engagement data.</li>
        <li><strong>Technical data:</strong> information needed to keep you signed in and to operate the service securely.</li>
      </ul>

      <h2>3. How we use your data</h2>
      <p>We use your personal data to provide and improve the platform: to create and manage your account, deliver courses, personalise your learning pathway and recommendations, and support translation and analytics features.</p>
      <p className="legal-highlight">
        <strong>Use of your email address.</strong> We use your email address to communicate with
        you about the service and about education and AI more broadly — including messages about
        your courses and progress, new and updated content, developments in artificial intelligence
        and teaching, platform announcements, and related educational information. You can
        unsubscribe from non-essential emails at any time; we will still send essential messages
        such as password resets and important account or security notices.
      </p>

      <h2>4. Legal basis</h2>
      <p>
        We process your data on the basis of your consent (given at registration), the performance
        of our service to you, and our legitimate interest in operating and improving an educational
        platform. You may withdraw consent at any time.
      </p>

      <h2>5. Where your data is stored</h2>
      <p>
        Your data is stored on our own infrastructure within the European Union and is protected by
        appropriate technical and organisational measures. We do not sell your personal data.
      </p>

      <h2>6. Sharing</h2>
      <p>
        We only share data with service providers that help us operate the platform (for example,
        email delivery), under appropriate safeguards, and where required by law. Other users may
        see limited profile information only if you choose to make your profile public.
      </p>

      <h2>7. Your rights</h2>
      <p>Under the GDPR you have the right to:</p>
      <ul>
        <li>access the personal data we hold about you;</li>
        <li>request correction or deletion of your data;</li>
        <li>object to or restrict certain processing;</li>
        <li>withdraw consent and unsubscribe from communications;</li>
        <li>data portability, where applicable.</li>
      </ul>
      <p>To exercise these rights, contact <a href="mailto:info@aidea-hub.eu">info@aidea-hub.eu</a>.</p>

      <h2>8. Retention</h2>
      <p>
        We keep your personal data for as long as your account is active and as needed to provide
        the service. You may request deletion of your account, after which we will remove or
        anonymise your personal data except where retention is required by law.
      </p>

      <h2>9. Cookies and local storage</h2>
      <p>
        AIDEA uses your browser&rsquo;s local storage to keep you signed in. We do not use tracking
        or advertising cookies.
      </p>

      <h2>10. Changes and complaints</h2>
      <p>
        We may update this Policy; material changes will be notified through the platform. If you
        believe your data has been handled improperly, you may lodge a complaint with your national
        data protection authority (in Greece, the Hellenic Data Protection Authority).
      </p>
    </LegalLayout>
  )
}
