// Формаларды бақылау
document.addEventListener('submit', async (e) => {
    // Егер бұл нөмір қосу немесе өшіру формасы болса
    if (e.target.action.includes('plate') || e.target.action.includes('barrier')) {
        e.preventDefault(); // Беттің қайта жүктелуін тоқтату
        
        const formData = new FormData(e.target);
        await fetch(e.target.action, {
            method: 'POST',
            body: formData
        });

        // Беттің тек контентін жаңарту (немесе жай ғана бетті қайта жүктеу)
        window.location.reload(); 
    }
});
// Әр 5 секунд сайын бетті жаңартып тұру (тек логтарды)
setInterval(async () => {
    // Бұл жерде тек логтар бөлігін жаңартуға болады, 
    // бірақ әзірге қарапайым болу үшін бүкіл бетті жаңартайық
    // window.location.reload(); 
}, 5000);