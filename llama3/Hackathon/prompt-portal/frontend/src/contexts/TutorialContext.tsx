import React, { createContext, useContext, useState, useEffect } from 'react';
import Tutorial, { TutorialStep } from '../components/Tutorial';
import { useLocation } from 'react-router-dom';

interface TutorialContextType {
    runTutorial: (steps: TutorialStep[]) => void;
    isTutorialRunning: boolean;
}

const TutorialContext = createContext<TutorialContextType | undefined>(undefined);

export const TutorialProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [steps, setSteps] = useState<TutorialStep[]>([]);
    const [isRunning, setIsRunning] = useState(false);
    const location = useLocation();

    const runTutorial = React.useCallback((newSteps: TutorialStep[]) => {
        setSteps(newSteps);
        setIsRunning(true);
    }, []);

    const handleFinish = () => {
        setIsRunning(false);
        // Mark as seen for this specific route if needed
        localStorage.setItem(`tutorial_seen_${location.pathname}`, 'true');
    };

    const handleSkip = () => {
        setIsRunning(false);
    };

    return (
        <TutorialContext.Provider value={{ runTutorial, isTutorialRunning: isRunning }}>
            {children}
            <Tutorial
                steps={steps}
                run={isRunning}
                onFinish={handleFinish}
                onSkip={handleSkip}
            />
        </TutorialContext.Provider>
    );
};

export const useTutorial = () => {
    const context = useContext(TutorialContext);
    if (!context) {
        throw new Error('useTutorial must be used within a TutorialProvider');
    }
    return context;
};
