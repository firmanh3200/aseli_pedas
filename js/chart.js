/* AseliPedas - Helper Chart.js untuk histogram distribusi */
(function () {
  var chart = null;

  function destroy() {
    if (chart) { chart.destroy(); chart = null; }
  }
  window.destroyHist = destroy;

  window.drawHist = function (canvasId, cfg) {
    destroy();
    var el = document.getElementById(canvasId);
    if (!el || typeof Chart === 'undefined') return;

    var n = cfg.data.length;
    var colors = cfg.data.map(function (_, i) {
      var t = n <= 1 ? 0 : i / (n - 1);
      return 'hsla(' + Math.round(258 - 70 * t) + ', 86%, 64%, 0.92)';
    });
    var hovers = cfg.data.map(function (_, i) {
      var t = n <= 1 ? 0 : i / (n - 1);
      return 'hsla(' + Math.round(258 - 70 * t) + ', 90%, 74%, 1)';
    });

    chart = new Chart(el, {
      type: 'bar',
      data: {
        labels: cfg.labels,
        datasets: [{
          label: 'Frekuensi',
          data: cfg.data,
          backgroundColor: colors,
          hoverBackgroundColor: hovers,
          borderRadius: 8,
          borderSkipped: false,
          maxBarThickness: 46
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 700, easing: 'easeOutQuart' },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(13,20,36,.96)',
            borderColor: 'rgba(255,255,255,.14)',
            borderWidth: 1,
            titleColor: '#E7EBF4',
            bodyColor: '#B7C2D6',
            padding: 12,
            cornerRadius: 10,
            displayColors: false,
            callbacks: {
              title: function (items) { return 'Interval: ' + items[0].label; },
              label: function (item) {
                return 'Frekuensi: ' + item.parsed.y.toLocaleString('id-ID');
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            border: { color: 'rgba(255,255,255,.12)' },
            ticks: {
              color: '#8FA0B8', maxRotation: 45, autoSkip: true, maxTicksLimit: 12,
              font: { family: "'JetBrains Mono', monospace", size: 10 }
            }
          },
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(255,255,255,.06)' },
            border: { display: false },
            ticks: {
              color: '#8FA0B8', precision: 0,
              font: { family: "'JetBrains Mono', monospace", size: 10 }
            }
          }
        }
      }
    });
  };
})();
