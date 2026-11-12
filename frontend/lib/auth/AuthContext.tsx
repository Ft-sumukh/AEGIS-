"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { UserRole } from "@/lib/api/types";
import { api } from "@/lib/api/client";

interface AuthContextType {
  role: UserRole;
  setRole: (role: UserRole) => void;
  actorId: string;
  canAcknowledge: boolean;
  canInvestigate: boolean;
  canConfigure: boolean;
}

const AuthContext = createContext<AuthContextType>({
  role: "OPERATOR",
  setRole: () => {},
  actorId: "operator_ui",
  canAcknowledge: true,
  canInvestigate: true,
  canConfigure: false,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [role, setRoleState] = useState<UserRole>("OPERATOR");
  const actorId = `${role.toLowerCase()}_demo`;

  const setRole = (newRole: UserRole) => {
    setRoleState(newRole);
    api.setRole(newRole, `${newRole.toLowerCase()}_demo`);
  };

  useEffect(() => {
    api.setRole(role, actorId);
  }, [role, actorId]);

  const canAcknowledge = role === "OPERATOR" || role === "ADMIN";
  const canInvestigate = role === "ANALYST" || role === "OPERATOR" || role === "ADMIN";
  const canConfigure = role === "ADMIN";

  return (
    <AuthContext.Provider
      value={{
        role,
        setRole,
        actorId,
        canAcknowledge,
        canInvestigate,
        canConfigure,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
