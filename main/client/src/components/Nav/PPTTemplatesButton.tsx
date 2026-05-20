import React, { useCallback } from 'react';
import { Presentation } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { TooltipAnchor, Button } from '@librechat/client';

interface PPTTemplatesButtonProps {
  isSmallScreen?: boolean;
  toggleNav: () => void;
}

export default function PPTTemplatesButton({
  isSmallScreen,
  toggleNav,
}: PPTTemplatesButtonProps) {
  const navigate = useNavigate();

  const handleClick = useCallback(() => {
    navigate('/templates');
    if (isSmallScreen) {
      toggleNav();
    }
  }, [navigate, isSmallScreen, toggleNav]);

  return (
    <TooltipAnchor
      description="PPT 模板库"
      render={
        <Button
          variant="outline"
          data-testid="nav-ppt-templates-button"
          aria-label="PPT 模板库"
          className="rounded-full border-none bg-transparent p-2 hover:bg-surface-hover md:rounded-xl"
          onClick={handleClick}
        >
          <Presentation className="icon-lg text-text-primary" aria-hidden="true" />
        </Button>
      }
    />
  );
}
