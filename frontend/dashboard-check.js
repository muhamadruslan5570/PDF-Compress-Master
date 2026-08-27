
    (function () {
      const user = localStorage.getItem('mr_pdf_user');
      if (!user) {
        window.location.replace('../index.html');
      }
    })();
  


  (() => {
    const mobileMenu = document.getElementById('mobileMenu');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    function closeSidebar() {
      sidebar.classList.remove('is-open');
      sidebarOverlay.classList.remove('is-open');
      document.body.classList.remove('sidebar-open');
    }

    if (mobileMenu) {
      mobileMenu.addEventListener('click', () => {
        sidebar.classList.toggle('is-open');
        sidebarOverlay.classList.toggle('is-open');
        document.body.classList.toggle('sidebar-open');
      });
    }

    if (sidebarOverlay) {
      sidebarOverlay.addEventListener('click', closeSidebar);
    }

    document.querySelectorAll('.sidebar-link').forEach(link => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 820) {
          closeSidebar();
        }
      });
    });

    // 1. AMBIL DATA PROFIL DARI BACKEND FASTAPI
    async function loadDashboardProfile() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/profile/`);

        if (response.status === 401) {
          localStorage.removeItem('mr_pdf_user');
          window.location.replace('../index.html');
          return;
        }

        if (!response.ok) return;

        const data = await response.json();
        const name = data.name || 'User';
        const email = data.email || 'user@example.com';
        const plan = data.plan || 'FREE';
        const firstLetter = name.charAt(0).toUpperCase();

        const headerName = document.getElementById('headerUserName');
        const welcomeName = document.getElementById('welcomeUserName');
        const profileName = document.getElementById('profileName');
        const profileEmail = document.getElementById('profileEmail');
        const headerAvatar = document.getElementById('headerAvatar');
        const profileAvatar = document.getElementById('profileAvatar');
        const headerPlan = document.getElementById('headerUserPlan');
        const currentPlan = document.getElementById('currentPlan');

        if (headerName) headerName.textContent = name;
        if (welcomeName) welcomeName.textContent = name;
        if (profileName) profileName.textContent = name;
        if (profileEmail) profileEmail.textContent = email;
        if (headerPlan) headerPlan.textContent = plan + ' Plan';
        if (currentPlan) currentPlan.textContent = plan;

        // Render foto profile/avatar jika tersedia di backend
        if (data.avatar_url) {
          const fullAvatarUrl = data.avatar_url.startsWith('http')
            ? data.avatar_url
            : `${API_BASE_URL}${data.avatar_url}?t=${new Date().getTime()}`;

          if (headerAvatar) {
            headerAvatar.style.backgroundImage = `url('${fullAvatarUrl}')`;
            headerAvatar.textContent = '';
          }
          if (profileAvatar) {
            profileAvatar.style.backgroundImage = `url('${fullAvatarUrl}')`;
            profileAvatar.textContent = '';
          }
        } else {
          if (headerAvatar) {
            headerAvatar.style.backgroundImage = 'none';
            headerAvatar.textContent = firstLetter;
          }
          if (profileAvatar) {
            profileAvatar.style.backgroundImage = 'none';
            profileAvatar.textContent = firstLetter;
          }
        }
      } catch (error) {
        console.error('Error loading profile in dashboard:', error);
      }
    }

    // 2. AMBIL DATA STATISTIK DASHBOARD DARI ENDPOINT /api/history/stats
    async function loadDashboardStats() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/history/stats`);

        if (!response.ok) {
          throw new Error('Gagal mengambil statistik');
        }

        const data = await response.json();
        const stats = data.stats || {};

        const statPdfs = document.getElementById('statPdfs');
        const statStorage = document.getElementById('statStorage');
        const statAi = document.getElementById('statAi');
        const statAccountStatus = document.getElementById('statAccountStatus');

        if (statPdfs) {
          statPdfs.textContent = stats.pdfs_processed ?? 0;
        }

        if (statStorage) {
          statStorage.textContent = stats.storage_used || '0 MB';
        }

        if (statAi) {
          statAi.textContent = stats.ai_requests ?? 0;
        }

        if (statAccountStatus) {
          statAccountStatus.textContent = stats.account_status || 'ACTIVE';
        }

      } catch (error) {
        console.error('Error loading dashboard statistics:', error);
      }
    }

    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
      logoutButton.addEventListener('click', (event) => {
        event.preventDefault();
        localStorage.removeItem('mr_pdf_user');
        window.location.replace('../index.html');
      });
    }

    const sidebarLinks = document.querySelectorAll('.sidebar-link[href^="#"]');
    sidebarLinks.forEach(link => {
      link.addEventListener('click', () => {
        sidebarLinks.forEach(item => item.classList.remove('active'));
        link.classList.add('active');
      });
    });

    // PANGGIL KEDUA FUNGSI SAAT HALAMAN DIMUAT
    loadDashboardProfile();
    loadDashboardStats();
  })();

