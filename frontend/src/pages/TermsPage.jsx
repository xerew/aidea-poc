import { useTranslation } from 'react-i18next'
import LegalLayout from '../components/LegalLayout'

export default function TermsPage() {
  const { t } = useTranslation()
  return (
    <LegalLayout title={t('legal.termsTitle')}>
      <p>
        These Terms of Service (&ldquo;Terms&rdquo;) govern your use of the AIDEA platform
        (&ldquo;AIDEA&rdquo;, &ldquo;the platform&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;),
        an educational service operated by the Information Management Unit of the Institute of
        Communication and Computer Systems (ICCS). By creating an account or using the platform,
        you agree to these Terms and to our Privacy Policy.
      </p>

      <h2>1. Who can use AIDEA</h2>
      <p>
        AIDEA is intended for teachers and educators. You must provide accurate registration
        information, keep your credentials confidential, and are responsible for all activity
        under your account. You must be legally able to enter into these Terms.
      </p>

      <h2>2. Your account</h2>
      <p>
        You are responsible for maintaining the security of your account. Notify us promptly of any
        unauthorised use. We may suspend or terminate accounts that violate these Terms or that are
        used unlawfully.
      </p>

      <h2>3. Acceptable use</h2>
      <p>You agree not to:</p>
      <ul>
        <li>use the platform for any unlawful purpose or in breach of any applicable regulation;</li>
        <li>upload content that is illegal, infringing, harmful, or that you do not have the right to share;</li>
        <li>attempt to disrupt, reverse-engineer, or gain unauthorised access to the platform or its data;</li>
        <li>misrepresent your identity or impersonate others.</li>
      </ul>

      <h2>4. Content and intellectual property</h2>
      <p>
        Course materials and platform software are owned by ICCS or its partners and are provided
        for your educational use. Content you create or upload remains yours; by uploading it you
        grant us a licence to host, display and process it to operate the platform.
      </p>

      <h2>5. AI-generated content</h2>
      <p>
        AIDEA uses artificial intelligence for features such as content translation and
        recommendations. AI outputs may contain errors and should be reviewed before being relied
        upon. AI-assisted translations are provided as an aid and may be reviewed by a human before
        being considered validated.
      </p>

      <h2>6. Communications</h2>
      <p>
        By registering, you agree that we may contact you by email as described in our Privacy
        Policy, including messages about your courses, new content, developments in AI and
        education, and platform updates. You can opt out of non-essential communications at any time.
      </p>

      <h2>7. Availability and changes</h2>
      <p>
        We aim to keep the platform available but do not guarantee uninterrupted access. We may
        update, suspend, or discontinue features, and we may amend these Terms; material changes
        will be notified through the platform.
      </p>

      <h2>8. Disclaimers and liability</h2>
      <p>
        The platform is provided &ldquo;as is&rdquo; without warranties of any kind. To the extent
        permitted by law, we are not liable for indirect or consequential damages arising from your
        use of the platform.
      </p>

      <h2>9. Governing law</h2>
      <p>
        These Terms are governed by the laws of Greece and applicable European Union law. Disputes
        are subject to the competent courts of Greece.
      </p>

      <h2>10. Contact</h2>
      <p>
        Questions about these Terms can be sent to <a href="mailto:info@aidea-hub.eu">info@aidea-hub.eu</a>.
      </p>
    </LegalLayout>
  )
}
