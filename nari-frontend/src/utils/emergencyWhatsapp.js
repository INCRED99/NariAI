/**
 * emergencyWhatsapp.js
 * Shared utility for instantly opening WhatsApp with a pre-filled SOS message.
 * Used across ChatPage (safe word / risk=100%), EmergencyPage, and SosModal.
 * Never asks the user for confirmation — opens immediately.
 */

/**
 * Normalise a phone number to international format (no +, no spaces).
 * Assumes Indian numbers (prefix 91) if 10 digits starting with 6-9.
 */
export const cleanPhone = (phone) => {
  if (!phone) return null;
  let clean = String(phone).replace(/[\s\-\(\)\+]/g, '');
  if (clean.length === 10 && '6789'.includes(clean[0])) clean = '91' + clean;
  return clean;
};

/**
 * Build the SOS message text.
 * @param {string} situation   - Human-readable situation text
 * @param {object} locationInfo - { latitude, longitude, locationName }
 */
export const buildSosMessage = (situation, { latitude, longitude, locationName } = {}) => {
  const loc =
    locationName ||
    (latitude && longitude
      ? `${Number(latitude).toFixed(4)}°N, ${Number(longitude).toFixed(4)}°E`
      : 'Unknown location');

  const mapLink =
    latitude && longitude
      ? `\n🗺️ Live Map: https://maps.google.com/?q=${latitude},${longitude}`
      : '';

  const now = new Date();
  const timeStr =
    now.toLocaleDateString() +
    ' ' +
    now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  return (
    `🚨 NARI SOS ALERT!\n` +
    `- SITUATION: ${situation}\n` +
    `- LOCATION: ${loc}${mapLink}\n` +
    `- TIME: ${timeStr}\n\n` +
    `Please send help immediately!`
  );
};

/**
 * Immediately open WhatsApp for a given contact with a pre-filled SOS message.
 * Falls back to window.location.href if the popup was blocked.
 *
 * @param {string} phone   - Raw phone string (e.g. '7007914594' or '+91 70079 14594')
 * @param {string} message - Pre-built SOS message
 */
export const openWhatsAppNow = (phone, message) => {
  const ph = cleanPhone(phone);
  if (!ph) return; // No phone — abort silently
  const url = `https://wa.me/${ph}?text=${encodeURIComponent(message)}`;
  const win = window.open(url, '_blank');
  if (!win || win.closed || typeof win.closed === 'undefined') {
    window.location.href = url;
  }
};

/**
 * One-stop helper: build message + open WhatsApp for the first emergency contact.
 *
 * @param {string} situation    - Short description of the emergency
 * @param {object} locationInfo - { latitude, longitude, locationName }
 * @param {Array}  contacts     - Array of { name, phone } (uses first contact)
 */
export const triggerWhatsAppSos = (situation, locationInfo = {}, contacts = []) => {
  if (!contacts || contacts.length === 0) return; // No contacts set — do nothing
  const firstContact = contacts[0];
  if (!firstContact?.phone) return;
  const message = buildSosMessage(situation, locationInfo);
  openWhatsAppNow(firstContact.phone, message);
};
