window.formatTimestamp = function(iso) {
    const date = new Date(iso);
    return date.toLocaleString('en-GB', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
      hour12: false
    });
  };
  
  window.reverseGeocode = async function(lat, lng) {
    const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`;
    const res = await fetch(url);
    const data = await res.json();
    return data.display_name || "Unknown location";
  };
  
  