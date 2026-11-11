/**
 * Student Dashboard Interactive Logic
 * Intelligent Course Recommendation System
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Live Course Search and Filter
    const courseSearchInput = document.getElementById("courseSearchInput");
    const difficultyFilter = document.getElementById("difficultyFilter");
    const courseCards = document.querySelectorAll(".course-item-card");

    function filterCourses() {
        const query = (courseSearchInput ? courseSearchInput.value : "").toLowerCase().trim();
        const difficulty = (difficultyFilter ? difficultyFilter.value : "all");

        courseCards.forEach(card => {
            const courseName = card.getAttribute("data-course-name") || "";
            const courseCode = card.getAttribute("data-course-code") || "";
            const courseDiff = card.getAttribute("data-difficulty") || "";
            const courseTags = card.getAttribute("data-tags") || "";

            const textMatch = courseName.includes(query) || courseCode.includes(query) || courseTags.includes(query);
            const diffMatch = difficulty === "all" || courseDiff.toLowerCase() === difficulty.toLowerCase();

            if (textMatch && diffMatch) {
                card.style.display = "";
            } else {
                card.style.display = "none";
            }
        });
    }

    if (courseSearchInput) {
        courseSearchInput.addEventListener("input", filterCourses);
    }
    if (difficultyFilter) {
        difficultyFilter.addEventListener("change", filterCourses);
    }

    // 2. Interest selection counter
    const interestCheckboxes = document.querySelectorAll(".interest-checkbox");
    const selectedCountBadge = document.getElementById("selectedInterestsCount");

    function updateInterestCounter() {
        if (!selectedCountBadge) return;
        const count = document.querySelectorAll(".interest-checkbox:checked").length;
        selectedCountBadge.textContent = count;
    }

    interestCheckboxes.forEach(cb => {
        cb.addEventListener("change", updateInterestCounter);
    });
    updateInterestCounter();
});
