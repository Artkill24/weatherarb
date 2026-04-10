(function() {
    // Trova lo script corrente per leggere i parametri (città)
    var scripts = document.getElementsByTagName('script');
    var currentScript = scripts[scripts.length - 1];
    var city = currentScript.getAttribute('data-city') || 'milano';
    var theme = currentScript.getAttribute('data-theme') || 'dark';

    // Crea il container del widget
    var containerId = 'wa-widget-' + Math.random().toString(36).substr(2, 9);
    document.write('<div id="' + containerId + '"></div>');

    // Stili CSS iniettati
    var styles = `
        .wa-w { font-family: sans-serif; border-radius: 12px; padding: 16px; width: 280px; transition: all .3s; }
        .wa-w-dark { background: #0f1117; color: white; border: 1px solid #1f2937; }
        .wa-w-light { background: #f9fafb; color: #111827; border: 1px solid #e5e7eb; }
        .wa-w-head { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.6; margin-bottom: 8px; }
        .wa-w-main { display: flex; justify-content: space-between; align-items: center; }
        .wa-w-city { font-weight: bold; font-size: 16px; }
        .wa-w-z { font-family: monospace; font-size: 20px; font-weight: bold; }
        .wa-w-foot { margin-top: 12px; font-size: 11px; display: flex; justify-content: space-between; align-items: center; }
        .wa-w-link { color: #3b82f6; text-decoration: none; font-weight: 600; }
    `;
    var styleSheet = document.createElement("style");
    styleSheet.innerText = styles;
    document.head.appendChild(styleSheet);

    // Fetch dei dati
    fetch('https://api.weatherarb.com/api/v1/pulse/' + city.toLowerCase())
        .then(response => response.json())
        .then(data => {
            var z = data.weather.z_score;
            var lv = data.weather.anomaly_level;
            var color = lv === 'CRITICAL' ? '#ef4444' : (lv === 'EXTREME' ? '#f97316' : '#3b82f6');
            
            var html = `
                <div class="wa-w wa-w-${theme}">
                    <div class="wa-w-head">Weather Intelligence Status</div>
                    <div class="wa-w-main">
                        <div class="wa-w-city">${data.province}</div>
                        <div class="wa-w-z" style="color: ${color}">${z > 0 ? '+' : ''}${z.toFixed(2)}</div>
                    </div>
                    <div class="wa-w-foot">
                        <span style="color: ${color}; font-weight: bold">${lv}</span>
                        <a href="https://weatherarb.com/it/${city.toLowerCase()}/" class="wa-w-link" target="_blank">Full Intel →</a>
                    </div>
                </div>
            `;
            document.getElementById(containerId).innerHTML = html;
        })
        .catch(err => console.error('WeatherArb Widget Error:', err));
})();
