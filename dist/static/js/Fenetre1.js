// Fenetre1.js - Overlay flottant frontend pour afficher deux flèches rotatives et une vitesse
// Cette implémentation ne dépend d'aucun backend. Elle crée un panneau draggable au-dessus de la carte.

(function(global){
  const STATE = {
    created: false,
    visible: false,
    angleTrue: 120, // Orientation initiale à 90° sans utiliser de timer
    angleApp: 90,
    timerTrue: null,
    timerApp: null,
    el: null,
    canvas0: null,
    canvas1: null,
    speedEl: null,
    speedAl: null,
    AttitudeTrue: 45, // Élément DOM affichant l'attitude (Tribord/Bâbord) pour le vrai vent
    AttitudeApp: 30,  // Élément DOM affichant l'attitude (Tribord/Bâbord) pour le vent apparent
    drag: { active: false, x: 0, y: 0, left: 30, top: 0 }
  };

  function ensureCreated(){
    if (STATE.created) return;

    // Créer le conteneur
    const box = document.createElement('div');
    box.id = 'fenetre1-overlay';
    Object.assign(box.style, {
      position: 'relative',
      left: STATE.drag.left + '%',
      top: STATE.drag.top + '3px',
      width: '485px',
      height: 'auto',
      background: 'rgba(255, 255, 255,0.75)',
      color: '#0',
      borderRadius: '10px',
      padding: '10px',
      zIndex: 10000,
      display: 'none',
      userSelect: 'none',
      cursor: 'move',
      boxShadow: '0 6px 20px rgba(0,0,0,0.4)'
    });

    // Titre simple
    const title = document.createElement('div');
    title.textContent = 'VENTS';
    title.style.textAlign = 'center';
    title.style.fontSize = '16px';
    title.style.marginBottom = '6px';
    title.style.fontFamily = 'Arial, sans-serif';
    title.style.fontWeight = 'bold';
    title.style.color = 'white';
    title.style.visibility = 'hidden';

    // Deux cadrans : chaque canvas dans un conteneur pour sur imprimer une icône centrée
    const row = document.createElement('div');
    Object.assign(row.style, {
      display: 'flex',
      flexWrap: 'nowrap',
      justifyContent: 'space-between',
      alignItems: 'center',
      gap: '0px',
      width: '100%'
    });

    // Crée un conteneur colonne (gauche/droite)
    function makeDial(iconSrc, iconAlt){
      const wrap = document.createElement('div');
      Object.assign(wrap.style, { position: 'relative', width: '49%', aspectRatio: '2 / 1', display: 'block' });

      const canvas = document.createElement('canvas');
      // Taille interne pour un rendu net
      canvas.width = 300;
      canvas.height = 150;
      Object.assign(canvas.style, { width: '100%', height: 'auto', display: 'block', position: 'relative', zIndex: 2 });

      const img = document.createElement('img');
      img.src = iconSrc;
      img.alt = iconAlt;
      Object.assign(img.style, {
        position: 'absolute',
        left: '50%',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        maxWidth: '228px',
        maxHeight: '228px',
        zIndex: 1,
        pointerEvents: 'none'
      });

      wrap.appendChild(canvas);
      wrap.appendChild(img);
      return {wrap, canvas};
    }

    const left = makeDial('./static/icone/vent_R.png', 'Vent relatif');
    const right = makeDial('./static/icone/vent_A.png', 'Vent apparent');

    row.appendChild(left.wrap);
    row.appendChild(right.wrap);

    // Stocker les références canvas
    const canvas0 = left.canvas;
    const canvas1 = right.canvas;

    box.appendChild(title);
    box.appendChild(row);


  // Conteneur horizontal pour afficher exactement 3 informations :
  // 1) Vitesse vent réel 2) Attitude vent réel (ex : 45° Bd) 3) Vitesse vent apparent
  const speedWrap = document.createElement('div');
  Object.assign(speedWrap.style, {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '20px',
    marginTop: '30px'
  });

  // Styles communs
  const baseFont = 'Arial, sans-serif';
  const baseSize = '12px';
  const baseWeight = 'bold';

  // Vitesse réelle (libellé à mettre à jour dynamiquement)
  const speedLabelTrue = document.createElement('span');
  Object.assign(speedLabelTrue.style, {
    fontFamily: baseFont,
    fontSize: baseSize,
    fontWeight: baseWeight,
    color: 'blue',
    minWidth: '110px',
    textAlign: 'center'
  });

  // Attitude vent réel (ex: "45° Bd")
  const attitudeTrue = document.createElement('span');
  attitudeTrue.id = 'fenetre1-attitude-true';
  attitudeTrue.textContent = '';
  Object.assign(attitudeTrue.style, {
    fontFamily: baseFont,
    fontSize: baseSize,
    fontWeight: baseWeight,
    color: '#0066cc',
    minWidth: '110px',
    textAlign: 'center'
  });
  attitudeTrue.title = 'Attitude (angle° + Td/Bd) – Vent vrai';

  // Vitesse vent apparent (libellé à mettre à jour dynamiquement)
  const speedLabelApp = document.createElement('span');
  Object.assign(speedLabelApp.style, {
    fontFamily: baseFont,
    fontSize: baseSize,
    fontWeight: baseWeight,
    color: 'blue',
    minWidth: '110px',
    textAlign: 'center'
  });

  // Ajouter les 3 éléments dans le conteneur horizontal
  speedWrap.appendChild(speedLabelTrue);
  speedWrap.appendChild(attitudeTrue);
  speedWrap.appendChild(speedLabelApp);

  // Ajouter le conteneur dans box
  box.appendChild(speedWrap);

  // Conserver les références originales, mais rediriger vers les 3 spans
  STATE.speedEl = speedLabelTrue;
  STATE.speedAl = speedLabelApp;
  STATE.AttitudeTrue = attitudeTrue;
  STATE.AttitudeApp = null;



    // Insérer au-dessus de la carte (avant #map pour garantir z index supérieur)
    const map = document.getElementById('map') || document.body;
    map.parentNode.insertBefore(box, map.nextSibling);

    // Drag logic
    const onMouseDown = (e)=>{
      STATE.drag.active = true;
      STATE.drag.x = e.clientX;
      STATE.drag.y = e.clientY;
      e.preventDefault();
    };
    const onMouseMove = (e)=>{
      if(!STATE.drag.active) return;
      const dx = e.clientX - STATE.drag.x;
      const dy = e.clientY - STATE.drag.y;
      STATE.drag.x = e.clientX;
      STATE.drag.y = e.clientY;
      STATE.drag.left += dx;
      STATE.drag.top += dy;
      box.style.left = STATE.drag.left + 'px';
      box.style.top = STATE.drag.top + 'px';
    };
    const onMouseUp = ()=>{ STATE.drag.active = false; };
    box.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    STATE.el = box;
    STATE.canvas0 = canvas0;
    STATE.canvas1 = canvas1;
    STATE.created = true;

    // Rendu initial sans timer
    const ctx0 = STATE.canvas0.getContext('2d');
    drawArrow(ctx0, STATE.angleTrue);
    const ctx1 = STATE.canvas1.getContext('2d');
    drawArrowAlt(ctx1, STATE.angleApp);
  }

  function drawArrow(ctx, angleDeg){// ---------------
    const w = ctx.canvas.width;
    const h = ctx.canvas.height;
    const cx = w / 2;
    const cy = h / 2; // centré pour éviter le rognage lors de la rotation

    ctx.clearRect(0,0,w,h);
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angleDeg * Math.PI / 180);
    ctx.translate(-cx, -cy);

    // Dimensions proportionnelles pour rester visibles quelle que soit l'orientation
    const radius = Math.min(w, h) / 2 - 10; // marge de 10 px
    const shaft = radius - 15;              // longueur de tige
    const headH = 20;                       // hauteur de la pointe
    const headW = 10;                       // largeur totale de la pointe

    // Dessin d'une flèche simple (triangle + tige) pour simuler fleche.svg
    ctx.fillStyle = '#FF0000';
    ctx.strokeStyle = '#FF0000';
    ctx.lineWidth = 6;

    // Tige
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx, cy - shaft);
    ctx.stroke();

    // Pointe (triangle)
    ctx.beginPath();
    ctx.moveTo(cx, cy - shaft - headH);
    ctx.lineTo(cx - headW/2, cy - shaft + 6);
    ctx.lineTo(cx + headW/2, cy - shaft + 6);
    ctx.closePath();
    ctx.fill();

    ctx.restore();
  }

  function drawArrowAlt(ctx, angleDeg){
    const w = ctx.canvas.width;
    const h = ctx.canvas.height;
    const cx = w / 2;
    const cy = h / 2; // centré comme l'autre flèche

    ctx.clearRect(0,0,w,h);
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angleDeg * Math.PI / 180);
    ctx.translate(-cx, -cy);

    // Dimensions proportionnelles
    const radius = Math.min(w, h) / 2 - 10;
    const shaft = radius - 15;
    const headH = 20;
    const headW = 10;

    // Variante de couleur pour simuler fleche1.svg
    ctx.fillStyle = '#336633';
    ctx.strokeStyle = '#336633';
    ctx.lineWidth = 6;

    // Tige
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx, cy - shaft);
    ctx.stroke();

    // Pointe (triangle)
    ctx.beginPath();
    ctx.moveTo(cx, cy - shaft - headH);
    ctx.lineTo(cx - headW/2, cy - shaft + 6);
    ctx.lineTo(cx + headW/2, cy - shaft + 6);
    ctx.closePath();
    ctx.fill();

    ctx.restore();
  }

  // Deprecated : plus besoin de timers côté frontend. Conserve la fonction pour compatibilité, mais ne fait rien.
  function startTimers(){
    // ne plus démarrer d'intervalles, au besoin, on arrête les éventuels timers existants
    stopTimers();
  }

  function stopTimers(){
    if (STATE.timerTrue){ clearInterval(STATE.timerTrue); STATE.timerTrue = null; }
    if (STATE.timerApp){ clearInterval(STATE.timerApp); STATE.timerApp = null; }
  }

  // Lecture périodique douce des coordonnées globales (mise à jour si la fenêtre est visible)
  function updateFromCoordinates(){
    try {
      if (!window || !window.coordinates) return;
      const c = window.coordinates;
      // Vitesse réelle et apparente
      if (typeof c.w_speed_true !== 'undefined') setSpeed(c.w_speed_true);
      if (typeof c.w_speed_app !== 'undefined') setSpeedA(c.w_speed_app);

      // Angles vrais / apparents
      const hasTrueAngle = typeof c.w_angle_true !== 'undefined';
      const hasAppAngle  = typeof c.w_angle_app  !== 'undefined';
      if (hasTrueAngle) setAngleTrue(c.w_angle_true);
      if (hasAppAngle)  setAngleApp(c.w_angle_app);

      // Attitude : UNIQUEMENT pour le vent réel. Pas d'attitude pour l'apparent.
      const spTrue = Number(c.w_speed_true) || 0;

      if (spTrue > 0 && hasTrueAngle) {
        // Si un libellé de vraie attitude est fourni, on l'utilise pour le côté (Td/Bd),
        // tout en affichant l'angle depuis le vrai angle.
        if (typeof c.w_attitude_true === 'undefined') {
           setAttitudeTrue(c.w_angle_true);
        } else {
            setAttitudeTrue(c.w_attitude_true);
        }
      } else {
        // vitesse nulle/absente ou pas d'angle : ne rien afficher
        setAttitudeTrue('');
      }

      // Ne pas afficher ni gérer d'attitude pour le vent apparent (exigence utilisateur)
      // On nettoie au cas où un ancien état subsisterait.
      if (STATE.AttitudeApp) {
        STATE.AttitudeApp.textContent = '';
      }
    } catch (e) {
      // silencieux
    }
  }

  function startPolling(){
    if (STATE._pollId) return;
    STATE._pollId = setInterval(()=>{
      if (STATE.visible){
        updateFromCoordinates();
      }
    }, 500);
  }

  function stopPolling(){
    if (STATE._pollId){
      clearInterval(STATE._pollId);
      STATE._pollId = null;
    }
  }

  function init(){
    if (STATE.created) return;
    ensureCreated();
  }

  function toggle(show){
    init();
    STATE.visible = !!show;
    STATE.el.style.display = STATE.visible ? 'block' : 'none';
    // Démarre/arrête l'actualisation auto depuis window.coordinates
    if (STATE.visible){
      startPolling();
      // Mise à jour immédiate à l'ouverture
      updateFromCoordinates();
    } else {
      stopPolling();
    }
  }

  function setSpeed(knots){
    init();
    const v = Number(knots);
    if (!isNaN(v)){
      STATE.speedEl.textContent = v.toFixed(1) + ' Nds';
    }
  }

  function setSpeedA(knots){
    init();
    const v = Number(knots);
    if (!isNaN(v)){
      STATE.speedAl.textContent = v.toFixed(1) + ' Nds';
    }
  }

  // Map valeur vers 'Td' (tribord) ou 'Bd' (bâbord)
  function mapAttitude(val){
    if (val === null || val === undefined) return '';
    if (typeof val === 'string'){
      const s = val.trim().toLowerCase();
      if (s.includes('td') || s.includes('tribord')) return 'Td';
      if (s.includes('bd') || s.includes('babord')) return 'Bd';
      const maybe = Number(s);
      if (!isNaN(maybe)) return computeAttitudeFromAngle(maybe);
      return '';
    }
    if (typeof val === 'number'){
      return computeAttitudeFromAngle(val);
    }
    return '';
  }

  function computeAttitudeFromAngle(angle){
    const a = normalizeDeg(angle);
    if (a === null) return '';
    // Convention : 0° = face à l'étrave, 90° = tribord, 270° = bâbord
    // Td si angle dans 0,180, Bd si angle dans 180,360
    return (a >= 0 && a < 180) ? 'Td' : 'Bd';
  }

  // Retourne un angle dans l'intervalle [0,180] pour l'affichage de l'angle au vent (symétrie Td/Bd)
  function reduceAngleTo180(angle){
    const a = normalizeDeg(angle);
    if (a === null) return null;
    return a <= 180 ? a : (360 - a);
  }
  // Retourne un angle dans l'intervalle [0,90] (angle aigu au vent)
  function reduceAngleTo90(angle){
    const a = normalizeDeg(angle);
    if (a === null) return null;
    const r = a <= 180 ? a : (360 - a);
    return r <= 90 ? r : (180 - r);
  }
  function angle90Enabled(){
    try { return localStorage.getItem('angle90') === '1'; } catch(e){ return false; }
  }

  function setAttitudeTrue(val){
    init();
    // Déterminer le côté (Td/Bd) à partir de val (qui peut être un angle, ou un libellé)
    let side = mapAttitude(val);
    // Déterminer l'angle à afficher : prioriser STATE.angleTrue si dispo, sinon val si c'est un nombre
    let angleDisplay = null;
    const fromState = STATE.angleTrue;
    const reducer = angle90Enabled() ? reduceAngleTo90 : reduceAngleTo180;
    if (typeof fromState === 'number') {
      angleDisplay = reducer(fromState);
      if (!side) side = computeAttitudeFromAngle(fromState);
    } else if (typeof val === 'number') {
      angleDisplay = reducer(val);
      if (!side) side = computeAttitudeFromAngle(val);
    }

    // Si on n'a pas d'angle ou pas de côté, ne rien afficher
    if (STATE.AttitudeTrue) {
      if (angleDisplay !== null && side) {
        STATE.AttitudeTrue.textContent = Math.round(angleDisplay) + '° ' + side;
      } else {
        STATE.AttitudeTrue.textContent = '';
      }
    }
  }

  function setAttitudeApp(val){
    init();
    const lab = mapAttitude(val);
    if (STATE.AttitudeApp) STATE.AttitudeApp.textContent = lab;
  }

  // Permettre de piloter les angles depuis l'extérieur
  function normalizeDeg(val){
    // remet l'angle dans [0,360)
    let v = Number(val);
    if (isNaN(v)) return null;
    v = v % 360;
    if (v < 0) v += 360;
    return v;
  }

  function setAngles(angleTrue, angleApp){
    init();
    const ctx0 = STATE.canvas0.getContext('2d');
    const ctx1 = STATE.canvas1.getContext('2d');

    if (angleTrue !== undefined && angleTrue !== null){
      const v0 = normalizeDeg(angleTrue);
      if (v0 !== null){
        STATE.angleTrue = v0;
        drawArrow(ctx0, STATE.angleTrue);
      }
    }
    if (angleApp !== undefined && angleApp !== null){
      const v1 = normalizeDeg(angleApp);
      if (v1 !== null){
        STATE.angleApp = v1;
        drawArrowAlt(ctx1, STATE.angleApp);
      }
    }
  }

  function setAngleTrue(angle){
    setAngles(angle, null);
  }

  function setAngleApp(angle){
    setAngles(null, angle);
  }

  // Auto-init DOM ready pour être prêt dès le chargement
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Rafraîchir l'affichage si le mode change
  try {
    window.addEventListener('angle90change', function(){
      // réafficher l'attitude avec le nouvel angle réduit
      setAttitudeTrue(STATE.angleTrue);
    });
  } catch(e) {}

  // Exposer une API minimale
  global.Fenetre1 = {
    init,
    toggle,
    setSpeed,
    setSpeedA,
    setAngles,
    setAngleTrue,
    setAngleApp,
    setAttitudeTrue,
    setAttitudeApp
  };
})(window);
