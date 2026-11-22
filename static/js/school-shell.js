(() => {
  const back = document.querySelector('.back-to-top');
  const navbar = document.querySelector('.navbar');
  function updateNavigation() {
    if (back) back.hidden = window.scrollY < 200;
    if (navbar) navbar.classList.toggle('menu-bg', !document.querySelector('body > .nav-hero') || window.scrollY > 100);
  }
  window.addEventListener('scroll', updateNavigation, {passive: true});
  updateNavigation();
  if (back) back.addEventListener('click', (event) => {
    event.preventDefault();
    window.scrollTo({top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
  });
  document.querySelectorAll('.navbar-collapse a').forEach((link) => link.addEventListener('click', () => {
    if (window.innerWidth < 992) bootstrap.Collapse.getOrCreateInstance(link.closest('.navbar-collapse'), {toggle: false}).hide();
  }));
})();
