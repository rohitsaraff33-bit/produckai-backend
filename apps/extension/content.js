// Content script for Jira pages
console.log('ProduckAI extension loaded on Jira page');

// Add a visual indicator that the extension is active
const indicator = document.createElement('div');
indicator.innerHTML = '🦆 ProduckAI Active';
indicator.style.cssText = `
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: #3b82f6;
  color: white;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  z-index: 10000;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
`;

document.body.appendChild(indicator);

// Remove indicator after 3 seconds
setTimeout(() => {
  indicator.style.transition = 'opacity 0.5s';
  indicator.style.opacity = '0';
  setTimeout(() => indicator.remove(), 500);
}, 3000);
