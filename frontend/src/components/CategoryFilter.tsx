import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDownIcon, ChevronRight } from "lucide-react";
import React from "react";
import { CardContent } from "./ui/card";
import { Label } from "./ui/label";
import { Button } from "./ui/button";

interface CategoryFilterProps {
  category: string;
  categoryOptions: Record<string, string[]>;
  onCategoryChange: (category: string) => void;
}

export const CategoryFilter: React.FC<CategoryFilterProps> = ({
  category,
  categoryOptions,
  onCategoryChange,
}) => {
  const appendPath = (path: string, option: string) => {
    if (path != "") return path + ">" + option;
    else return option;
  };
  const subPaths = category.split(">").map((elem, i, arr) => ({
    elem,
    path: arr.slice(0, i + 1).join(">"),
    prev: arr.slice(0, i).join(">"),
  }));
  const breadcrumbs =
    category !== "" &&
    subPaths.map((subPath) => (
      <React.Fragment key={subPath.path}>
        <BreadcrumbItem className="border rounded-md bg-popover p-2">
          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-1">
              {subPath.elem}
              <ChevronDownIcon className="size-3.5" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuGroup>
                {(categoryOptions[subPath.prev] || []).map((option) => (
                  <DropdownMenuItem
                    key={option}
                    onClick={() =>
                      onCategoryChange(appendPath(subPath.prev, option))
                    }
                  >
                    {option}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </BreadcrumbItem>
        <BreadcrumbSeparator>
          <ChevronRight />
        </BreadcrumbSeparator>
      </React.Fragment>
    ));
  return (
    <CardContent className="border-b  pb-4 space-y-2">
      <div className="flex items-center justify-between">
        <Label>Category Filter</Label>
        <Button variant="ghost" size="sm" onClick={() => onCategoryChange("")}>
          Clear
        </Button>
      </div>
      <Breadcrumb>
        <BreadcrumbList>
          {breadcrumbs}{" "}
          <BreadcrumbItem className="border rounded-md bg-popover p-2">
            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center gap-1">
                ...
                <ChevronDownIcon className="size-3.5" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuGroup>
                  {(categoryOptions[category] || []).map((option) => (
                    <DropdownMenuItem
                      key={option}
                      onClick={() =>
                        onCategoryChange(appendPath(category, option))
                      }
                    >
                      {option}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    </CardContent>
  );
};
