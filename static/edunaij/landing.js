(() => {
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const progress = document.querySelector('.edu-scroll-progress');
  let frame = 0;

  function paintProgress() {
    frame = 0;
    const distance = document.documentElement.scrollHeight - window.innerHeight;
    const fraction = distance > 0 ? Math.max(0, Math.min(1, window.scrollY / distance)) : 0;
    progress.style.transform = `scaleX(${fraction})`;
  }

  function queueProgress() {
    if (!frame) frame = window.requestAnimationFrame(paintProgress);
  }

  if (progress) {
    window.addEventListener('scroll', queueProgress, { passive: true });
    window.addEventListener('resize', queueProgress);
    queueProgress();
  }

  if ('IntersectionObserver' in window && !motion.matches) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        if (!motion.matches) entry.target.classList.add('edu-in-view');
      });
    }, { rootMargin: '0px 0px -5% 0px' });
    document.querySelectorAll('[data-reveal]').forEach((element) => observer.observe(element));
  }

  const guide = document.querySelector('.edu-tour-guide');
  const focus = document.querySelector('.edu-focus');
  if (!guide || !focus) return;

  const stops = {
    overview: { bounds: ['21.5%', '27%', '75%', '21%'], text: 'See enrolment, staffing, classes and parent accounts at a glance.' },
    setup: { bounds: ['68%', '49.5%', '28%', '50%'], text: 'Follow the setup checklist from school profile to first enrolment.' },
    navigation: { bounds: ['0.8%', '31.5%', '17.2%', '59%'], text: 'Open students, teachers, academics and admissions from the sidebar.' },
  };
  const buttons = Array.from(guide.querySelectorAll('[data-tour]'));
  const note = guide.querySelector('.edu-tour-note');

  function showStop(active) {
    const stop = stops[active.dataset.tour];
    const [left, top, width, height] = stop.bounds;
    Object.assign(focus.style, { left, top, width, height });
    note.textContent = stop.text;
    buttons.forEach((button) => button.setAttribute('aria-pressed', String(button === active)));
  }

  buttons.forEach((button) => button.addEventListener('click', () => showStop(button)));
  showStop(buttons[0]);
  guide.hidden = false;
  focus.hidden = false;
})();
