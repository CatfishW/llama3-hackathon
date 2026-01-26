import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, ChevronLeft, X, CheckCircle } from 'lucide-react';

export interface TutorialStep {
    target: string; // CSS Selector
    title: string;
    content: string;
    position?: 'top' | 'bottom' | 'left' | 'right' | 'center';
    allowMultiple?: boolean;
}

interface TutorialProps {
    steps: TutorialStep[];
    onFinish?: () => void;
    onSkip?: () => void;
    run?: boolean;
}

const Tutorial: React.FC<TutorialProps> = ({ steps, onFinish, onSkip, run = false }) => {
    const [currentStep, setCurrentStep] = useState(0);
    const [targetRect, setTargetRect] = useState<DOMRect | null>(null);
    const [isVisible, setIsVisible] = useState(run);
    const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth < 768);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const updateTargetRect = useCallback(() => {
        if (currentStep < steps.length) {
            const element = document.querySelector(steps[currentStep].target);
            if (element) {
                setTargetRect(element.getBoundingClientRect());
                element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else if (steps[currentStep].allowMultiple) {
                const elements = document.querySelectorAll(steps[currentStep].target);
                if (elements.length > 0) {
                    setTargetRect(elements[0].getBoundingClientRect());
                    elements[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    setTargetRect(null);
                }
            } else {
                setTargetRect(null);
            }
        }
    }, [currentStep, steps]);

    useEffect(() => {
        if (run) {
            setIsVisible(true);
            updateTargetRect();
        } else {
            setIsVisible(false);
        }
    }, [run, updateTargetRect]);

    useEffect(() => {
        window.addEventListener('resize', updateTargetRect);
        window.addEventListener('scroll', updateTargetRect);
        return () => {
            window.removeEventListener('resize', updateTargetRect);
            window.removeEventListener('scroll', updateTargetRect);
        };
    }, [updateTargetRect]);

    const handleNext = () => {
        if (currentStep < steps.length - 1) {
            setCurrentStep(prev => prev + 1);
        } else {
            setIsVisible(false);
            onFinish?.();
        }
    };

    const handlePrev = () => {
        if (currentStep > 0) {
            setCurrentStep(prev => prev - 1);
        }
    };

    const handleSkip = () => {
        setIsVisible(false);
        onSkip?.();
    };

    if (!isVisible || steps.length === 0) return null;

    const step = steps[currentStep];
    const position = step.position || 'bottom';

    // Calculate popover position
    const getPopoverStyle = (): React.CSSProperties => {
        if (isMobile) {
            return {
                bottom: '24px',
                left: '24px',
                right: '24px',
                width: 'auto',
                maxWidth: 'calc(100vw - 48px)',
                transform: 'none'
            };
        }

        if (!targetRect) return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };

        const offset = 20;
        const popoverWidth = 320;
        const popoverHeight = 200; // Estimated max height
        let top = 0;
        let left = 0;
        let transform = '';

        switch (position) {
            case 'top':
                top = targetRect.top - offset - popoverHeight; // This is a rough estimate
                left = targetRect.left + targetRect.width / 2;
                transform = 'translate(-50%, -100%)';
                // More precise calculation using CSS
                return {
                    bottom: (window.innerHeight - targetRect.top) + offset,
                    left: Math.max(180, Math.min(window.innerWidth - 180, targetRect.left + targetRect.width / 2)),
                    transform: 'translateX(-50%)'
                };
            case 'bottom':
                return {
                    top: targetRect.bottom + offset,
                    left: Math.max(180, Math.min(window.innerWidth - 180, targetRect.left + targetRect.width / 2)),
                    transform: 'translateX(-50%)'
                };
            case 'left':
                left = targetRect.left - offset - popoverWidth;
                if (left < 20) {
                    // Flip to right
                    return { top: targetRect.top + targetRect.height / 2, left: targetRect.right + offset, transform: 'translateY(-50%)' };
                }
                return { top: targetRect.top + targetRect.height / 2, left: targetRect.left - offset - popoverWidth, transform: 'translateY(-50%)' };
            case 'right':
                left = targetRect.right + offset;
                if (left + popoverWidth > window.innerWidth - 20) {
                    // Flip to left
                    return { top: targetRect.top + targetRect.height / 2, right: (window.innerWidth - targetRect.left) + offset, transform: 'translateY(-50%)' };
                }
                return { top: targetRect.top + targetRect.height / 2, left: targetRect.right + offset, transform: 'translateY(-50%)' };
            default:
                return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };
        }
    };

    return (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9999, overflow: 'hidden', pointerEvents: 'none' }}>
            {/* Background Overlay with hole */}
            <svg style={{ position: 'absolute', width: '100%', height: '100%', pointerEvents: 'auto' }}>
                <defs>
                    <mask id="tutorial-mask">
                        <rect x="0" y="0" width="100%" height="100%" fill="white" />
                        {targetRect && (
                            <motion.rect
                                initial={false}
                                animate={{
                                    x: targetRect.x - 8,
                                    y: targetRect.y - 8,
                                    width: targetRect.width + 16,
                                    height: targetRect.height + 16,
                                    rx: 12
                                }}
                                fill="black"
                            />
                        )}
                    </mask>
                </defs>
                <rect
                    x="0"
                    y="0"
                    width="100%"
                    height="100%"
                    fill="rgba(0, 0, 0, 0.7)"
                    mask="url(#tutorial-mask)"
                    style={{ backdropFilter: 'blur(4px)' }}
                    onClick={handleSkip}
                />
            </svg>

            {/* Popover */}
            <AnimatePresence mode="wait">
                <motion.div
                    key={currentStep}
                    initial={{ opacity: 0, scale: 0.9, y: 10 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9, y: 10 }}
                    transition={{ type: 'spring', damping: 20, stiffness: 300 }}
                    style={{
                        position: 'absolute',
                        width: isMobile ? 'auto' : '320px',
                        background: 'rgba(30, 41, 59, 0.95)',
                        backdropFilter: 'blur(16px)',
                        borderRadius: '24px',
                        padding: isMobile ? '20px' : '24px',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
                        pointerEvents: 'auto',
                        color: 'white',
                        ...getPopoverStyle()
                    }}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#6366f1' }}>
                            Step {currentStep + 1} of {steps.length}
                        </span>
                        <button
                            onClick={handleSkip}
                            style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
                        >
                            <X size={18} />
                        </button>
                    </div>

                    <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '8px', color: '#f8fafc' }}>
                        {step.title}
                    </h3>
                    <p style={{ fontSize: '0.95rem', color: '#94a3b8', lineHeight: 1.6, marginBottom: '24px' }}>
                        {step.content}
                    </p>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <button
                            onClick={handlePrev}
                            disabled={currentStep === 0}
                            style={{
                                background: 'rgba(255,255,255,0.05)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                color: currentStep === 0 ? '#475569' : '#f8fafc',
                                padding: '8px 12px',
                                borderRadius: '12px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontSize: '0.85rem',
                                cursor: currentStep === 0 ? 'not-allowed' : 'pointer'
                            }}
                        >
                            <ChevronLeft size={16} /> Back
                        </button>

                        <button
                            onClick={handleNext}
                            style={{
                                background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                                border: 'none',
                                color: 'white',
                                padding: '8px 20px',
                                borderRadius: '12px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                fontSize: '0.85rem',
                                fontWeight: 600,
                                cursor: 'pointer',
                                boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
                            }}
                        >
                            {currentStep === steps.length - 1 ? (
                                <>Finish <CheckCircle size={16} /></>
                            ) : (
                                <>Next <ChevronRight size={16} /></>
                            )}
                        </button>
                    </div>
                </motion.div>
            </AnimatePresence>

            {/* Highlight glow */}
            {targetRect && (
                <motion.div
                    initial={false}
                    animate={{
                        x: targetRect.x - 8,
                        y: targetRect.y - 8,
                        width: targetRect.width + 16,
                        height: targetRect.height + 16,
                    }}
                    style={{
                        position: 'absolute',
                        borderRadius: '12px',
                        border: '2px solid rgba(99, 102, 241, 0.5)',
                        boxShadow: '0 0 20px rgba(99, 102, 241, 0.3)',
                        pointerEvents: 'none'
                    }}
                />
            )}
        </div>
    );
};

export default Tutorial;
